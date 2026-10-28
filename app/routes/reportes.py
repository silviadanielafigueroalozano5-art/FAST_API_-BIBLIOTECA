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
from app.core.database import get_db
from app.schemas.reportes import (
    LibroMasPrestado,
    LibrosPorCategoria,
    PrestamoVencido,
    ReporteAutor,
    Resumen,
    SocioConMulta,
)

reportes_router = APIRouter(prefix="/reportes", tags=["Reportes"])


# GET /reportes/libros-mas-prestados?limit=10
@reportes_router.get("/libros-mas-prestados", response_model=list[LibroMasPrestado])
def ruta_libros_mas_prestados(
    limite: int | None = Query(default=None, ge=1, le=100, description="Tamaño del top"),
    limit: int = Query(default=10, ge=1, le=100, description="Alias de limite"),
    db: Session = Depends(get_db),
):
    return libros_mas_prestados(db, limite or limit)


# GET /reportes/categorias — incluye categorías con 0 libros
@reportes_router.get("/categorias", response_model=list[LibrosPorCategoria])
def ruta_libros_por_categoria(db: Session = Depends(get_db)):
    return libros_por_categoria(db)


# GET /reportes/prestamos-vencidos — ordenados por días de retraso desc
@reportes_router.get("/prestamos-vencidos", response_model=list[PrestamoVencido])
def ruta_prestamos_vencidos(db: Session = Depends(get_db)):
    return prestamos_vencidos(db)


# GET /reportes/socios-con-multas — solo socios con multa > 0
@reportes_router.get("/socios-con-multas", response_model=list[SocioConMulta])
def ruta_socios_con_multas(db: Session = Depends(get_db)):
    return socios_con_multas(db)


# GET /reportes/autores — libros y préstamos por autor
@reportes_router.get("/autores", response_model=list[ReporteAutor])
def ruta_reporte_autores(db: Session = Depends(get_db)):
    return reporte_autores(db)


# GET /reportes/resumen — totales generales de la biblioteca
@reportes_router.get("/resumen", response_model=Resumen)
def ruta_resumen(db: Session = Depends(get_db)):
    return resumen(db)
