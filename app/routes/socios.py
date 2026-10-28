"""ROUTES - Socios (Fase 4B).

Las rutas reciben la petición HTTP, validan con los esquemas Pydantic
y llaman al controlador (app/controllers/socios.py).

El DELETE de socio es especial: puede responder 200 (borrado lógico)
o 204 (eliminación física si nunca tuvo préstamos).
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.controllers.socios import (
    actualizar_socio,
    crear_socio,
    eliminar_socio,
    listar_socios,
    obtener_socio,
    prestamos_del_socio,
)
from app.core.database import get_db
from app.core.paginacion import paginacion
from app.schemas.prestamo import PrestamoResponse
from app.schemas.socio import SocioCrear, SocioResponse, SocioUpdate

socios_router = APIRouter(prefix="/socios", tags=["Socios"])


# CREAR (POST /socios) — 409 si el email ya existe
@socios_router.post(
    "", response_model=SocioResponse, status_code=status.HTTP_201_CREATED
)
def ruta_crear_socio(datos: SocioCrear, db: Session = Depends(get_db)):
    return crear_socio(db, datos)


# LISTAR (GET /socios) — paginado + filtro opcional ?activo=true|false
@socios_router.get("", response_model=list[SocioResponse])
def ruta_listar_socios(
    activo: bool | None = Query(
        default=None, description="Filtra por estado del socio"
    ),
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    return listar_socios(db, pag["skip"], pag["limit"], activo)


# OBTENER UNO (GET /socios/{socio_id})
@socios_router.get("/{socio_id}", response_model=SocioResponse)
def ruta_obtener_socio(socio_id: int, db: Session = Depends(get_db)):
    return obtener_socio(db, socio_id)


# ACTUALIZAR (PATCH /socios/{socio_id})
@socios_router.patch("/{socio_id}", response_model=SocioResponse)
def ruta_actualizar_socio(
    socio_id: int, datos: SocioUpdate, db: Session = Depends(get_db)
):
    return actualizar_socio(db, socio_id, datos)


# ELIMINAR (DELETE /socios/{socio_id})
# - Con préstamos SIN devolver: 409 (no se puede).
# - Solo con préstamos ya devueltos: borrado LÓGICO -> 200 con activo=false.
# - Sin préstamos: eliminación física -> 204 sin contenido.
@socios_router.delete("/{socio_id}")
def ruta_eliminar_socio(socio_id: int, db: Session = Depends(get_db)):
    resultado = eliminar_socio(db, socio_id)
    if resultado["eliminado"]:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return resultado["socio"]


# HISTORIAL DEL SOCIO (GET /socios/{socio_id}/prestamos)
# Filtro opcional: ?estado=activo | vencido | devuelto (o todo si se omite)
@socios_router.get("/{socio_id}/prestamos", response_model=list[PrestamoResponse])
def ruta_prestamos_del_socio(
    socio_id: int,
    estado: str | None = Query(
        default=None,
        description="activo | vencido | devuelto (omite para ver todo el historial)",
    ),
    db: Session = Depends(get_db),
):
    return prestamos_del_socio(db, socio_id, estado)
