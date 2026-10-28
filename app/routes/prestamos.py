"""ROUTES - Préstamos (Fase 4).

Las rutas reciben la petición HTTP, validan con los esquemas Pydantic
y llaman al controlador (app/controllers/prestamos.py), que aplica las
reglas de negocio (disponibilidad del libro, socio activo, devoluciones).

Las rutas de socios viven en app/routes/socios.py.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers.prestamos import (
    crear_prestamo,
    devolver_prestamo,
    listar_prestamos,
    obtener_prestamo,
)
from app.core.database import get_db
from app.core.paginacion import paginacion
from app.schemas.prestamo import (
    PrestamoCrear,
    PrestamoDevolucion,
    PrestamoDevolucionIn,
    PrestamoResponse,
)

prestamos_router = APIRouter(prefix="/prestamos", tags=["Prestamos"])


# CREAR PRÉSTAMO (POST /prestamos)
# Reglas: fecha no futura, dias 1-30 (default 14), socio activo,
# ejemplares libres, máximo 3 activos, sin multas pendientes.
@prestamos_router.post("", response_model=PrestamoResponse, status_code=status.HTTP_201_CREATED)
def ruta_crear_prestamo(datos: PrestamoCrear, db: Session = Depends(get_db)):
    return crear_prestamo(db, datos)


# LISTAR (GET /prestamos) — paginado + FILTROS COMBINABLES
# ?estado=activo|vencido|devuelto  ?socio_id=  ?libro_id=
@prestamos_router.get("", response_model=list[PrestamoResponse])
def ruta_listar_prestamos(
    estado: str | None = Query(
        default=None, description="activo | vencido | devuelto"
    ),
    socio_id: int | None = Query(default=None, gt=0, description="Filtra por socio"),
    libro_id: int | None = Query(default=None, gt=0, description="Filtra por libro"),
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    return listar_prestamos(
        db, pag["skip"], pag["limit"], estado=estado, socio_id=socio_id, libro_id=libro_id
    )


# OBTENER UNO (GET /prestamos/{prestamo_id}) — incluye estado calculado y multa
@prestamos_router.get("/{prestamo_id}", response_model=PrestamoResponse)
def ruta_obtener_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    return obtener_prestamo(db, prestamo_id)


# REGISTRAR DEVOLUCIÓN (POST /prestamos/{prestamo_id}/devolucion)
# R9: 409 si ya devuelto; 422 si la fecha es anterior al préstamo.
# R10: multa = días de retraso × 0,50.
@prestamos_router.post(
    "/{prestamo_id}/devolucion",
    response_model=PrestamoDevolucion,
    status_code=status.HTTP_200_OK,
)
def ruta_devolver_prestamo(
    prestamo_id: int,
    datos: PrestamoDevolucionIn | None = None,
    db: Session = Depends(get_db),
):
    fecha = datos.fecha_devolucion if datos else None
    prestamo = devolver_prestamo(db, prestamo_id, fecha)
    retraso = (prestamo.fecha_devolucion - prestamo.fecha_limite).days
    return PrestamoDevolucion(
        id=prestamo.id,
        fecha_devolucion=prestamo.fecha_devolucion,
        multa=prestamo.multa,
        dias_retraso=max(retraso, 0),
    )
