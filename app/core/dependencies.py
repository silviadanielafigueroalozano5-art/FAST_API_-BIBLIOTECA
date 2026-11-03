"""Dependencias compartidas de base de datos, autenticación y roles."""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NoAutenticado, Prohibido
from app.core.security import decodificar_token
from app.models.usuario import RolUsuario, Usuario

SessionDep = Annotated[Session, Depends(get_db)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]
) -> Usuario:
    try:
        payload = decodificar_token(token)
        if payload.get("type") != "access":
            raise NoAutenticado("Tipo de token inválido")
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise NoAutenticado("Token inválido o vencido") from exc

    usuario = db.get(Usuario, user_id)
    if usuario is None:
        raise NoAutenticado("Token inválido o vencido")
    if not usuario.activo:
        raise Prohibido("Usuario inactivo")
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def requiere_rol(*roles: RolUsuario):
    def verificar(usuario: CurrentUser) -> Usuario:
        if usuario.rol not in roles:
            raise Prohibido("No tiene permisos para esta acción")
        return usuario

    return Depends(verificar)


Staff = Annotated[
    Usuario, requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)
]
Admin = Annotated[Usuario, requiere_rol(RolUsuario.admin)]
SocioUser = Annotated[Usuario, requiere_rol(RolUsuario.socio)]
