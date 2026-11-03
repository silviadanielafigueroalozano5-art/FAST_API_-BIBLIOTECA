"""Administración de socios y endpoints de autoservicio."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select

from app.controllers.socios import (
    actualizar_socio,
    crear_socio,
    eliminar_socio,
    listar_socios,
    obtener_socio,
    prestamos_del_socio,
)
from app.core.dependencies import Admin, SessionDep, SocioUser, Staff
from app.core.exceptions import NoEncontrado
from app.core.openapi import RESPUESTAS_COMUNES
from app.models.prestamo import Prestamo
from app.schemas.pagina import Pagina
from app.schemas.prestamo import PrestamoResponse
from app.schemas.socio import (
    SocioActualizarPropio,
    SocioCrear,
    SocioResponse,
    SocioUpdate,
)

socios_router = APIRouter(
    prefix="/socios", tags=["Socios"], responses=RESPUESTAS_COMUNES
)


@socios_router.get(
    "/me",
    response_model=SocioResponse,
    summary="Consultar mi perfil de socio",
    responses={401: {"description": "No autenticado"}, 404: {"description": "Perfil no encontrado"}},
)
def ruta_mi_perfil(usuario: SocioUser, db: SessionDep):
    if usuario.socio_id is None:
        raise NoEncontrado("El usuario no tiene un perfil de socio")
    return obtener_socio(db, usuario.socio_id)


@socios_router.patch(
    "/me",
    response_model=SocioResponse,
    summary="Actualizar mi perfil",
    responses={401: {"description": "No autenticado"}, 422: {"description": "Campo no permitido"}},
)
def ruta_actualizar_mi_perfil(
    datos: SocioActualizarPropio, usuario: SocioUser, db: SessionDep
):
    if usuario.socio_id is None:
        raise NoEncontrado("El usuario no tiene un perfil de socio")
    return actualizar_socio(db, usuario.socio_id, datos)


@socios_router.get(
    "/me/prestamos",
    response_model=Pagina[PrestamoResponse],
    summary="Consultar mis préstamos",
    responses={401: {"description": "No autenticado"}},
)
def ruta_mis_prestamos(
    usuario: SocioUser,
    db: SessionDep,
    estado: str | None = Query(default=None, description="activo | vencido | devuelto"),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    if usuario.socio_id is None:
        raise NoEncontrado("El usuario no tiene un perfil de socio")
    items, total = prestamos_del_socio(
        db, usuario.socio_id, estado, skip=skip, limit=limit
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@socios_router.get(
    "/me/multas",
    summary="Consultar mis multas pendientes",
    responses={401: {"description": "No autenticado"}},
)
def ruta_mis_multas(
    usuario: SocioUser,
    db: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    if usuario.socio_id is None:
        raise NoEncontrado("El usuario no tiene un perfil de socio")
    consulta = select(Prestamo).where(
        Prestamo.socio_id == usuario.socio_id,
        Prestamo.multa > 0,
        Prestamo.multa_pagada.is_(False),
    )
    total = db.scalar(
        select(func.count()).select_from(consulta.subquery())
    ) or 0
    items = list(
        db.scalars(
            consulta.order_by(Prestamo.fecha_devolucion.desc())
            .offset(skip)
            .limit(limit)
        ).all()
    )
    total_adeudado = db.scalar(
        select(func.coalesce(func.sum(Prestamo.multa), 0)).where(
            Prestamo.socio_id == usuario.socio_id,
            Prestamo.multa > 0,
            Prestamo.multa_pagada.is_(False),
        )
    ) or Decimal("0")
    return {
        "items": [
            {
                "prestamo_id": item.id,
                "libro_id": item.libro_id,
                "multa": item.multa,
                "multa_pagada": item.multa_pagada,
                "fecha_devolucion": item.fecha_devolucion,
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
        "total_adeudado": total_adeudado,
    }


@socios_router.post(
    "",
    response_model=SocioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear socio",
)
def ruta_crear_socio(datos: SocioCrear, _: Staff, db: SessionDep):
    return crear_socio(db, datos)


@socios_router.get(
    "",
    response_model=Pagina[SocioResponse],
    summary="Listar socios",
)
def ruta_listar_socios(
    _: Staff,
    db: SessionDep,
    activo: bool | None = Query(default=None, description="Filtra por estado"),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    items, total = listar_socios(db, skip, limit, activo)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@socios_router.get(
    "/{socio_id}",
    response_model=SocioResponse,
    summary="Consultar socio",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Permiso insuficiente"}, 404: {"description": "Socio no encontrado"}},
)
def ruta_obtener_socio(socio_id: int, _: Staff, db: SessionDep):
    return obtener_socio(db, socio_id)


@socios_router.patch(
    "/{socio_id}",
    response_model=SocioResponse,
    summary="Actualizar socio",
)
def ruta_actualizar_socio(
    socio_id: int, datos: SocioUpdate, _: Staff, db: SessionDep
):
    return actualizar_socio(db, socio_id, datos)


@socios_router.delete(
    "/{socio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar socio",
)
def ruta_eliminar_socio(socio_id: int, _: Admin, db: SessionDep) -> Response:
    eliminar_socio(db, socio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@socios_router.get(
    "/{socio_id}/prestamos",
    response_model=Pagina[PrestamoResponse],
    summary="Consultar historial de un socio",
)
def ruta_prestamos_del_socio(
    socio_id: int,
    _: Staff,
    db: SessionDep,
    estado: str | None = Query(default=None, description="activo | vencido | devuelto"),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = prestamos_del_socio(
        db, socio_id, estado, skip=skip, limit=limit
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}
