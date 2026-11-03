"""CONTROLLER - Lógica de negocio de Socios (Fase 4B).

Reglas de negocio:
- El email es ÚNICO (se compara en minúsculas) -> 409 si duplicado.
- BORRADO LÓGICO: un socio con historial de préstamos no se elimina,
  se marca `activo=False`. Solo se borra de verdad si nunca prestó nada.
- Solo los socios ACTIVOS pueden crear préstamos (lo valida el
  controller de préstamos al usar obtener_socio).
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import Conflicto, NoEncontrado, ReglaNegocio
from app.models.prestamo import Prestamo
from app.models.socio import Socio
from app.models.usuario import Usuario


def _normalizar_email(valor: str | None) -> str | None:
    return valor.lower() if valor else valor


def crear_socio(db: Session, datos) -> Socio:
    email = _normalizar_email(datos.email)
    if db.scalar(select(Socio.id).where(Socio.email == email)) or db.scalar(
        select(Usuario.id).where(Usuario.email == email)
    ):
        raise Conflicto(f"Ya existe un socio con el email '{email}'")
    # email ya va normalizado en minúsculas: se excluye del dump
    socio = Socio(**datos.model_dump(exclude={"email"}), email=email)
    db.add(socio)
    db.commit()
    db.refresh(socio)
    return socio


def listar_socios(
    db: Session, skip: int = 0, limit: int = 20, activo: bool | None = None
) -> tuple[list[Socio], int]:
    consulta = select(Socio)
    if activo is not None:
        consulta = consulta.where(Socio.activo.is_(activo))
    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    items = list(db.scalars(consulta.offset(skip).limit(limit)).all())
    return items, total


def obtener_socio(db: Session, socio_id: int) -> Socio:
    socio = db.get(Socio, socio_id)
    if not socio:
        raise NoEncontrado(f"Socio con id={socio_id} no encontrado")
    return socio


def actualizar_socio(db: Session, socio_id: int, datos) -> Socio:
    socio = obtener_socio(db, socio_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "email" in cambios:
        email = _normalizar_email(cambios["email"])
        duplicado = db.scalar(select(Socio).where(Socio.email == email))
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        if (duplicado and duplicado.id != socio_id) or (
            usuario and usuario.socio_id != socio_id
        ):
            raise Conflicto(f"Ya existe un socio con el email '{email}'")
        cambios["email"] = email
    for campo, valor in cambios.items():
        setattr(socio, campo, valor)
    db.commit()
    db.refresh(socio)
    return socio


def eliminar_socio(db: Session, socio_id: int) -> dict:
    """Reglas de la fase 8:
    - Préstamos SIN devolver (activos o vencidos) -> 409.
    - Solo préstamos devueltos -> borrado lógico: activo=False, 204.
    - Sin préstamos -> eliminación física, 204.
    """
    socio = obtener_socio(db, socio_id)
    sin_devolver = db.scalar(
        select(func.count(Prestamo.id)).where(
            Prestamo.socio_id == socio_id, Prestamo.fecha_devolucion.is_(None)
        )
    )
    if sin_devolver:
        raise Conflicto(
            f"No se puede eliminar: el socio tiene {sin_devolver} préstamo(s) sin devolver"
        )
    total_prestamos = db.scalar(
        select(func.count(Prestamo.id)).where(Prestamo.socio_id == socio_id)
    )
    if total_prestamos:
        socio.activo = False
        db.commit()
        db.refresh(socio)
        # Fase 8: el borrado lógico responde 204 (sin contenido),
        # pero el socio queda activo=False en la BD
        return {"socio": None, "eliminado": True, "desactivado": True}
    db.delete(socio)
    db.commit()
    return {"socio": None, "eliminado": True}


# ---------- PRÉSTAMOS DEL SOCIO (GET /socios/{id}/prestamos) ----------


def prestamos_del_socio(
    db: Session,
    socio_id: int,
    estado: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Prestamo], int]:
    """Historial de préstamos de un socio con filtro opcional:

    - estado=activo   -> sin devolver
    - estado=vencido  -> sin devolver Y con la fecha de devolución
                         comprometida ya pasada (anterior a hoy)
    - estado=devuelto -> ya devueltos
    Sin ?estado= devuelve TODO el historial.
    """
    obtener_socio(db, socio_id)  # 404 si el socio no existe

    consulta = select(Prestamo).where(Prestamo.socio_id == socio_id)
    if estado == "activo":
        consulta = consulta.where(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite >= date.today(),
        )
    elif estado == "devuelto":
        consulta = consulta.where(Prestamo.fecha_devolucion.is_not(None))
    elif estado == "vencido":
        consulta = consulta.where(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite < date.today(),
        )
    elif estado is not None:
        raise ReglaNegocio(
            f"Estado '{estado}' no válido. Usa: activo, vencido o devuelto"
        )

    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    consulta = consulta.order_by(Prestamo.fecha_prestamo.desc())
    items = list(db.scalars(consulta.offset(skip).limit(limit)).all())
    return items, total
