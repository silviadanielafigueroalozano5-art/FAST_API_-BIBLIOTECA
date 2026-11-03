"""Administración de usuarios disponible únicamente para administradores."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.controllers.auth import (
    cambiar_estado_usuario,
    cambiar_rol,
    crear_usuario_staff,
    listar_usuarios,
)
from app.core.dependencies import Admin, SessionDep
from app.core.openapi import RESPUESTAS_COMUNES
from app.models.usuario import RolUsuario
from app.schemas.auth import (
    ActivoUpdate,
    RolUpdate,
    UsuarioCrear,
    UsuarioRespuesta,
)
from app.schemas.pagina import Pagina

router = APIRouter(
    prefix="/usuarios", tags=["Usuarios"], responses=RESPUESTAS_COMUNES
)


@router.get(
    "",
    response_model=Pagina[UsuarioRespuesta],
    summary="Listar usuarios",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Solo administradores"}},
)
def ruta_listar_usuarios(
    _: Admin,
    db: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    rol: RolUsuario | None = None,
    activo: bool | None = None,
):
    items, total = listar_usuarios(db, skip, limit, rol, activo)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post(
    "",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Crear bibliotecario o administrador",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Solo administradores"}},
)
def ruta_crear_usuario(datos: UsuarioCrear, _: Admin, db: SessionDep):
    return crear_usuario_staff(db, datos)


@router.patch(
    "/{usuario_id}/rol",
    response_model=UsuarioRespuesta,
    summary="Cambiar rol de usuario",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Solo administradores"}, 404: {"description": "Usuario no encontrado"}},
)
def ruta_cambiar_rol(
    usuario_id: int, datos: RolUpdate, actor: Admin, db: SessionDep
):
    return cambiar_rol(db, actor, usuario_id, datos.rol)


@router.patch(
    "/{usuario_id}/activo",
    response_model=UsuarioRespuesta,
    summary="Activar o desactivar usuario",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Solo administradores"}, 404: {"description": "Usuario no encontrado"}},
)
def ruta_cambiar_estado(
    usuario_id: int, datos: ActivoUpdate, actor: Admin, db: SessionDep
):
    return cambiar_estado_usuario(db, actor, usuario_id, datos.activo)
