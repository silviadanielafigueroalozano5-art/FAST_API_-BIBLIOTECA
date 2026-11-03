"""Registro y autenticación mediante OAuth2 Password y JWT."""

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from app.controllers.auth import (
    cambiar_password,
    cerrar_sesion,
    iniciar_sesion,
    registrar_usuario,
    renovar_tokens,
)
from app.core.dependencies import CurrentUser, SessionDep
from app.core.limiter import limiter
from app.core.openapi import RESPUESTAS_COMUNES
from app.schemas.auth import (
    PasswordChange,
    RefreshRequest,
    TokenRespuesta,
    UsuarioRegistro,
    UsuarioRespuesta,
)

router = APIRouter(
    prefix="/auth", tags=["Autenticación"], responses=RESPUESTAS_COMUNES
)


@router.post(
    "/registro",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un socio",
    responses={409: {"description": "El email ya está registrado"}},
)
@limiter.limit("5/minute")
def ruta_registro(
    request: Request, datos: UsuarioRegistro, db: SessionDep
) -> UsuarioRespuesta:
    return registrar_usuario(db, datos)


@router.post(
    "/login",
    response_model=TokenRespuesta,
    summary="Iniciar sesión",
    responses={401: {"description": "Credenciales inválidas"}, 423: {"description": "Cuenta bloqueada"}},
)
@limiter.limit("10/minute")
def ruta_login(
    request: Request,
    db: SessionDep,
    form: OAuth2PasswordRequestForm = Depends(),
):
    return iniciar_sesion(db, form.username, form.password)


@router.post(
    "/refresh",
    response_model=TokenRespuesta,
    summary="Rotar los tokens",
    responses={401: {"description": "Refresh token inválido o revocado"}},
)
def ruta_refresh(datos: RefreshRequest, db: SessionDep):
    return renovar_tokens(db, datos.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
    responses={401: {"description": "No autenticado"}},
)
def ruta_logout(
    datos: RefreshRequest,
    response: Response,
    usuario: CurrentUser,
    db: SessionDep,
) -> Response:
    cerrar_sesion(db, datos.refresh_token, usuario)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/me",
    response_model=UsuarioRespuesta,
    summary="Consultar el usuario autenticado",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Usuario inactivo"}},
)
def ruta_me(usuario: CurrentUser) -> UsuarioRespuesta:
    return usuario


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar contraseña",
    responses={401: {"description": "No autenticado"}, 422: {"description": "Contraseña actual incorrecta"}},
)
def ruta_cambiar_password(
    datos: PasswordChange, usuario: CurrentUser, db: SessionDep
) -> Response:
    cambiar_password(db, usuario, datos)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
