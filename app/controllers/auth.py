"""Casos de uso de registro, inicio de sesión y ciclo de vida JWT."""

from datetime import datetime, timedelta, timezone
import secrets
import jwt
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    CuentaBloqueada,
    Conflicto,
    NoAutenticado,
    NoEncontrado,
    Prohibido,
    ReglaNegocio,
)
from app.core.security import (
    crear_token,
    decodificar_token,
    hashear_password,
    verificar_password,
)
from app.models.refresh_token import RefreshToken
from app.models.socio import Socio
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auth import PasswordChange, UsuarioRegistro

DUMMY_PASSWORD_HASH = hashear_password(secrets.token_urlsafe(32))


def registrar_usuario(db: Session, datos: UsuarioRegistro) -> Usuario:
    email = str(datos.email).lower()
    if db.scalar(select(Usuario.id).where(Usuario.email == email)) or db.scalar(
        select(Socio.id).where(Socio.email == email)
    ):
        raise Conflicto("Ya existe un usuario o socio con ese email")

    socio = Socio(
        nombre=datos.nombre,
        email=email,
        telefono=datos.telefono,
        activo=True,
    )
    usuario = Usuario(
        email=email,
        nombre=datos.nombre,
        password_hash=hashear_password(datos.password),
        rol=RolUsuario.socio,
        activo=True,
        socio=socio,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise Conflicto("Ya existe un usuario o socio con ese email") from exc
    db.refresh(usuario)
    return usuario


def _crear_par_tokens(db: Session, usuario: Usuario) -> dict[str, int | str]:
    settings = get_settings()
    access_exp = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_exp = timedelta(days=settings.refresh_token_expire_days)
    access_token, _, _ = crear_token(usuario, "access", access_exp)
    refresh_token, jti, refresh_expira = crear_token(usuario, "refresh", refresh_exp)
    db.add(
        RefreshToken(
            jti=jti,
            usuario_id=usuario.id,
            expira_en=refresh_expira,
            revocado=False,
        )
    )
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_exp.total_seconds()),
    }


def iniciar_sesion(db: Session, email: str, password: str) -> dict[str, int | str]:
    email = email.strip().lower()
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    ahora = datetime.now(timezone.utc)
    password_valida = verificar_password(
        password, usuario.password_hash if usuario else DUMMY_PASSWORD_HASH
    )
    if usuario is None or not password_valida:
        if usuario is not None:
            bloqueado_hasta = usuario.bloqueado_hasta
            if bloqueado_hasta is not None and bloqueado_hasta.tzinfo is None:
                bloqueado_hasta = bloqueado_hasta.replace(tzinfo=timezone.utc)
            if bloqueado_hasta is None or bloqueado_hasta <= ahora:
                if bloqueado_hasta is not None:
                    usuario.intentos_fallidos = 0
                    usuario.bloqueado_hasta = None
                usuario.intentos_fallidos += 1
                if usuario.intentos_fallidos >= 5:
                    usuario.bloqueado_hasta = ahora + timedelta(minutes=15)
                db.commit()
        raise NoAutenticado("Credenciales inválidas")

    if usuario.bloqueado_hasta is not None:
        bloqueado_hasta = usuario.bloqueado_hasta
        if bloqueado_hasta.tzinfo is None:
            bloqueado_hasta = bloqueado_hasta.replace(tzinfo=timezone.utc)
        if bloqueado_hasta > ahora:
            raise CuentaBloqueada("Cuenta bloqueada temporalmente")
        usuario.bloqueado_hasta = None

    if not usuario.activo:
        db.commit()
        raise Prohibido("Usuario inactivo")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.flush()
    return _crear_par_tokens(db, usuario)


def renovar_tokens(db: Session, refresh_token: str) -> dict[str, int | str]:
    try:
        payload = decodificar_token(refresh_token)
        if payload.get("type") != "refresh":
            raise NoAutenticado("Tipo de token inválido")
        jti = str(payload["jti"])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise NoAutenticado("Refresh token inválido o vencido") from exc

    registro = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if registro is None:
        raise NoAutenticado("Refresh token inválido o vencido")
    if registro.revocado:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.usuario_id == registro.usuario_id)
            .values(revocado=True)
        )
        db.commit()
        raise NoAutenticado("Refresh token reutilizado; sesión revocada")

    ahora = datetime.now(timezone.utc)
    expira = registro.expira_en
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if registro.usuario_id != user_id or expira <= ahora:
        registro.revocado = True
        db.commit()
        raise NoAutenticado("Refresh token inválido o vencido")

    usuario = db.get(Usuario, user_id)
    if usuario is None or not usuario.activo:
        registro.revocado = True
        db.commit()
        raise NoAutenticado("Usuario inactivo o inexistente")

    registro.revocado = True
    db.flush()
    return _crear_par_tokens(db, usuario)


def cerrar_sesion(db: Session, refresh_token: str, usuario: Usuario) -> None:
    try:
        payload = decodificar_token(refresh_token)
        if payload.get("type") != "refresh":
            raise NoAutenticado("Tipo de token inválido")
        token_user_id = int(payload["sub"])
        jti = str(payload["jti"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise NoAutenticado("Refresh token inválido") from exc
    if token_user_id != usuario.id:
        raise NoAutenticado("El token no pertenece al usuario autenticado")
    registro = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if registro is not None:
        registro.revocado = True
        db.commit()


def cambiar_password(
    db: Session, usuario: Usuario, datos: PasswordChange
) -> None:
    if not verificar_password(datos.password_actual, usuario.password_hash):
        raise ReglaNegocio("La contraseña actual es incorrecta")
    usuario.password_hash = hashear_password(datos.password_nueva)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.usuario_id == usuario.id)
        .values(revocado=True)
    )
    db.commit()


def listar_usuarios(
    db: Session,
    skip: int,
    limit: int,
    rol: RolUsuario | None = None,
    activo: bool | None = None,
) -> tuple[list[Usuario], int]:
    consulta = select(Usuario)
    if rol is not None:
        consulta = consulta.where(Usuario.rol == rol)
    if activo is not None:
        consulta = consulta.where(Usuario.activo.is_(activo))
    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    items = list(db.scalars(consulta.offset(skip).limit(limit)).all())
    return items, total


def crear_usuario_staff(db: Session, datos) -> Usuario:
    email = str(datos.email).lower()
    if db.scalar(select(Usuario.id).where(Usuario.email == email)) or db.scalar(
        select(Socio.id).where(Socio.email == email)
    ):
        raise Conflicto(f"Ya existe un usuario con el email '{email}'")
    usuario = Usuario(
        email=email,
        nombre=datos.nombre,
        password_hash=hashear_password(datos.password),
        rol=datos.rol,
        activo=True,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise Conflicto(f"Ya existe un usuario con el email '{email}'") from exc
    db.refresh(usuario)
    return usuario


def cambiar_rol(db: Session, actor: Usuario, usuario_id: int, rol: RolUsuario) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NoEncontrado(f"Usuario con id={usuario_id} no encontrado")
    if actor.id == usuario.id and usuario.rol == RolUsuario.admin and rol != RolUsuario.admin:
        raise ReglaNegocio("Un administrador no puede quitarse su propio rol")
    if usuario.rol == RolUsuario.admin and usuario.activo and rol != RolUsuario.admin:
        total_admins = db.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.rol == RolUsuario.admin, Usuario.activo.is_(True)
            )
        )
        if total_admins <= 1:
            raise ReglaNegocio("Debe existir al menos un administrador activo")
    usuario.rol = rol
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.usuario_id == usuario.id)
        .values(revocado=True)
    )
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_estado_usuario(
    db: Session, actor: Usuario, usuario_id: int, activo: bool
) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NoEncontrado(f"Usuario con id={usuario_id} no encontrado")
    if actor.id == usuario.id and usuario.rol == RolUsuario.admin and not activo:
        raise ReglaNegocio("Un administrador no puede desactivarse a sí mismo")
    if usuario.rol == RolUsuario.admin and usuario.activo and not activo:
        total_admins = db.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.rol == RolUsuario.admin, Usuario.activo.is_(True)
            )
        )
        if total_admins <= 1:
            raise ReglaNegocio("Debe existir al menos un administrador activo")
    usuario.activo = activo
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.usuario_id == usuario.id)
        .values(revocado=True)
    )
    db.commit()
    db.refresh(usuario)
    return usuario
