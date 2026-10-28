"""Esquemas de respuesta de los reportes (Fase 6).

Cada reporte tiene su propio esquema y se resuelve con UNA SOLA
consulta SQL (los agregados se calculan en la BD, no en Python).
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LibroMasPrestado(BaseModel):
    """GET /reportes/libros-mas-prestados"""

    libro_id: int
    titulo: str
    autor: str
    total_prestamos: int


class LibrosPorCategoria(BaseModel):
    """GET /reportes/categorias — incluye las categorías con 0 libros."""

    categoria_id: int
    categoria: str
    total_libros: int


class PrestamoVencido(BaseModel):
    """GET /reportes/prestamos-vencidos"""

    prestamo_id: int
    titulo: str
    socio: str
    email: str
    fecha_limite: date
    dias_retraso: int = Field(description="fecha_limite - hoy, siempre > 0")


class SocioConMulta(BaseModel):
    """GET /reportes/socios-con-multas — solo socios con multa > 0."""

    socio_id: int
    nombre: str
    email: str
    multa_total: Decimal
    prestamos_vencidos: int


class ReporteAutor(BaseModel):
    """GET /reportes/autores"""

    autor_id: int
    autor: str
    total_libros: int
    total_prestamos: int


class Resumen(BaseModel):
    """GET /reportes/resumen — totales generales de la biblioteca."""

    total_libros: int
    total_ejemplares: int
    total_prestados: int  # préstamos sin devolver
    socios_activos: int
    socios_vencidos: int  # socios con préstamo vencido hoy
    multas_totales: Decimal
