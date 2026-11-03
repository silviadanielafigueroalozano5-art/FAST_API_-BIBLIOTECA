"""ROUTES - Reportes con agregados (Fase 6).

GET /reportes/... — cada endpoint delega en app/controllers/reportes.py,
que resuelve TODO con una sola consulta SQL (agregados en la BD).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.reportes import (
    libros_mas_prestados,
    libros_por_categoria,
    prestamos_vencidos,
    reporte_autores,
    resumen,
    socios_con_multas,
)
from app.core.dependencies import Staff
from app.core.database import get_db
from app.core.openapi import RESPUESTAS_COMUNES
from app.core.paginacion import paginacion
from app.schemas.pagina import Pagina
from app.schemas.reportes import (
    LibroMasPrestado,
    LibrosPorCategoria,
    PrestamoVencido,
    ReporteAutor,
    Resumen,
    SocioConMulta,
)

reportes_router = APIRouter(
    prefix="/reportes", tags=["Reportes"], responses=RESPUESTAS_COMUNES
)


# GET /reportes/libros-mas-prestados?limit=10
@reportes_router.get(
    "/libros-mas-prestados",
    response_model=Pagina[LibroMasPrestado],
    summary="Consultar los libros más prestados",
)
def ruta_libros_mas_prestados(
    _: Staff,
    limite: int | None = Query(default=None, ge=1, le=100, description="Tamaño del top"),
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    page_limit = limite or pag["limit"]
    items, total = libros_mas_prestados(db, page_limit, pag["skip"])
    return {"items": items, "total": total, "skip": pag["skip"], "limit": page_limit}


# GET /reportes/categorias — incluye categorías con 0 libros
@reportes_router.get(
    "/categorias", response_model=Pagina[LibrosPorCategoria],
    summary="Consultar el total de libros por categoría",
)
def ruta_libros_por_categoria(
    _: Staff, pag: dict = Depends(paginacion), db: Session = Depends(get_db)
):
    items, total = libros_por_categoria(db, pag["skip"], pag["limit"])
    return {"items": items, "total": total, **pag}


# GET /reportes/prestamos-vencidos — ordenados por días de retraso desc
@reportes_router.get(
    "/prestamos-vencidos", response_model=Pagina[PrestamoVencido],
    summary="Consultar préstamos vencidos",
)
def ruta_prestamos_vencidos(
    _: Staff, pag: dict = Depends(paginacion), db: Session = Depends(get_db)
):
    items, total = prestamos_vencidos(db, pag["skip"], pag["limit"])
    return {"items": items, "total": total, **pag}


# GET /reportes/socios-con-multas — solo socios con multa > 0
@reportes_router.get(
    "/socios-con-multas", response_model=Pagina[SocioConMulta],
    summary="Consultar socios con multas",
)
def ruta_socios_con_multas(
    _: Staff, pag: dict = Depends(paginacion), db: Session = Depends(get_db)
):
    items, total = socios_con_multas(db, pag["skip"], pag["limit"])
    return {"items": items, "total": total, **pag}


# GET /reportes/autores — libros y préstamos por autor
@reportes_router.get(
    "/autores", response_model=Pagina[ReporteAutor],
    summary="Consultar préstamos por autor",
)
def ruta_reporte_autores(
    _: Staff, pag: dict = Depends(paginacion), db: Session = Depends(get_db)
):
    items, total = reporte_autores(db, pag["skip"], pag["limit"])
    return {"items": items, "total": total, **pag}


# GET /reportes/resumen — totales generales de la biblioteca
@reportes_router.get(
    "/resumen", response_model=Resumen,
    summary="Consultar el resumen de la biblioteca",
)
def ruta_resumen(_: Staff, db: Session = Depends(get_db)):
    return resumen(db)
