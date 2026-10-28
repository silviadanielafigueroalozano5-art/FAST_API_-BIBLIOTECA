"""CONTROLLER - Reportes con agregados (Fase 6).

Cada reporte se resuelve con UNA SOLA consulta SQL:
- los agregados (COUNT, SUM) se calculan en PostgreSQL, no en Python;
- LEFT JOIN para no perder filas (categorías sin libros, autores sin
  préstamos, etc.);
- COALESCE para mostrar 0 en vez de NULL en los conteos.
"""

import os
from datetime import date
from decimal import Decimal

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.models.autor import Autor, Libro
from app.models.categoria import Categoria, libro_categoria
from app.models.prestamo import Prestamo
from app.models.socio import Socio

TASA_MULTA_DIARIA = Decimal(os.getenv("TASA_MULTA_DIARIA", "0.50"))


def libros_mas_prestados(db: Session, limit: int = 10) -> list[dict]:
    """Top de libros por nº de préstamos (incluye devueltos).

    UNA consulta: JOIN libros+autores, COUNT de préstamos agrupado.
    """
    filas = db.execute(
        select(
            Libro.id,
            Libro.titulo,
            Autor.nombre,
            func.count(Prestamo.id).label("total"),
        )
        .join(Autor, Libro.autor_id == Autor.id)
        .join(Prestamo, Prestamo.libro_id == Libro.id, isouter=True)
        .group_by(Libro.id, Libro.titulo, Autor.nombre)
        .order_by(func.count(Prestamo.id).desc(), Libro.titulo)
        .limit(limit)
    ).all()
    return [
        {"libro_id": lid, "titulo": titulo, "autor": autor, "total_prestamos": total}
        for lid, titulo, autor, total in filas
    ]


def libros_por_categoria(db: Session) -> list[dict]:
    """Nº de libros por categoría. UNA consulta con LEFT JOIN por la
    tabla intermedia N:M: las categorías SIN libros aparecen con 0.
    """
    filas = db.execute(
        select(
            Categoria.id,
            Categoria.nombre,
            func.count(libro_categoria.c.libro_id).label("total"),
        )
        .join(
            libro_categoria,
            libro_categoria.c.categoria_id == Categoria.id,
            isouter=True,
        )
        .group_by(Categoria.id, Categoria.nombre)
        .order_by(func.count(libro_categoria.c.libro_id).desc(), Categoria.nombre)
    ).all()
    return [
        {"categoria_id": cid, "categoria": nombre, "total_libros": total}
        for cid, nombre, total in filas
    ]


def prestamos_vencidos(db: Session) -> list[dict]:
    """Préstamos sin devolver con fecha_limite pasada, ordenados por
    retraso descendente. El retraso se calcula en SQL con
    CURRENT_DATE - fecha_limite.
    """
    filas = db.execute(
        select(
            Prestamo.id,
            Libro.titulo,
            Socio.nombre,
            Socio.email,
            Prestamo.fecha_limite,
            (date.today() - Prestamo.fecha_limite).label("retraso"),
        )
        .join(Libro, Prestamo.libro_id == Libro.id)
        .join(Socio, Prestamo.socio_id == Socio.id)
        .where(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite < date.today(),
        )
        .order_by(Prestamo.fecha_limite)
    ).all()
    return [
        {
            "prestamo_id": pid,
            "titulo": titulo,
            "socio": socio,
            "email": email,
            "fecha_limite": limite,
            "dias_retraso": retraso,
        }
        for pid, titulo, socio, email, limite, retraso in filas
    ]


def socios_con_multas(db: Session) -> list[dict]:
    """Socios con multa PENDIENTE > 0, ordenados por multa descendente.

    Multa pendiente = multas impagas (devueltos con multa_pagada=False)
    + retraso de vencidos sin devolver. Todo en UNA consulta: dos
    subconsultas agregadas por socio y LEFT JOIN con socios.
    """
    hoy = date.today()
    # Subconsulta 1: multas impagas de préstamos devueltos
    impagas_sq = (
        select(
            Prestamo.socio_id,
            func.sum(Prestamo.multa).label("impagas"),
        )
        .where(Prestamo.multa_pagada.is_(False))
        .group_by(Prestamo.socio_id)
        .subquery()
    )
    # Subconsulta 2: retraso acumulado de préstamos vencidos sin devolver
    retraso_sq = (
        select(
            Prestamo.socio_id,
            func.sum(
                func.greatest(cast(hoy - Prestamo.fecha_limite, Integer), 0)
            ).label("dias"),
            func.count(Prestamo.id).label("vencidos"),
        )
        .where(Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < hoy)
        .group_by(Prestamo.socio_id)
        .subquery()
    )
    filas = db.execute(
        select(
            Socio.id,
            Socio.nombre,
            Socio.email,
            func.coalesce(impagas_sq.c.impagas, 0)
            + func.coalesce(retraso_sq.c.dias, 0) * TASA_MULTA_DIARIA,
            func.coalesce(retraso_sq.c.vencidos, 0),
        )
        .join(impagas_sq, impagas_sq.c.socio_id == Socio.id, isouter=True)
        .join(retraso_sq, retraso_sq.c.socio_id == Socio.id, isouter=True)
        .where(
            (impagas_sq.c.impagas.is_not(None))
            | (retraso_sq.c.socio_id.is_not(None))
        )
        .order_by(
            (
                func.coalesce(impagas_sq.c.impagas, 0)
                + func.coalesce(retraso_sq.c.dias, 0) * TASA_MULTA_DIARIA
            ).desc()
        )
    ).all()
    return [
        {
            "socio_id": sid,
            "nombre": nombre,
            "email": email,
            "multa_total": multa or Decimal("0"),
            "prestamos_vencidos": vencidos,
        }
        for sid, nombre, email, multa, vencidos in filas
    ]


def reporte_autores(db: Session) -> list[dict]:
    """Por autor: nº de libros escritos y nº de préstamos totales.

    UNA consulta con 2 LEFT JOIN y COUNT(DISTINCT) para no duplicar
    (un libro puede tener varios préstamos; un autor varios libros).
    """
    filas = db.execute(
        select(
            Autor.id,
            Autor.nombre,
            func.count(func.distinct(Libro.id)).label("libros"),
            func.count(func.distinct(Prestamo.id)).label("prestamos"),
        )
        .join(Libro, Libro.autor_id == Autor.id, isouter=True)
        .join(Prestamo, Prestamo.libro_id == Libro.id, isouter=True)
        .group_by(Autor.id, Autor.nombre)
        .order_by(func.count(func.distinct(Prestamo.id)).desc(), Autor.nombre)
    ).all()
    return [
        {
            "autor_id": aid,
            "autor": nombre,
            "total_libros": libros,
            "total_prestamos": prestamos,
        }
        for aid, nombre, libros, prestamos in filas
    ]


def resumen(db: Session) -> dict:
    """Totales generales en UNA consulta (subconsultas escalares)."""
    total_prestados_sq = (
        select(func.count(Prestamo.id))
        .where(Prestamo.fecha_devolucion.is_(None))
        .scalar_subquery()
    )
    multas_sq = (
        select(
            func.coalesce(
                func.sum(
                    func.greatest(
                        cast(date.today() - Prestamo.fecha_limite, Integer), 0
                    )
                ),
                0,
            )
        )
        .where(
            Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < date.today()
        )
        .scalar_subquery()
    )
    socios_vencidos_sq = (
        select(func.count(func.distinct(Prestamo.socio_id)))
        .where(
            Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < date.today()
        )
        .scalar_subquery()
    )
    fila = db.execute(
        select(
            func.count(Libro.id),
            func.coalesce(func.sum(Libro.ejemplares), 0),
            total_prestados_sq,
            select(func.count(Socio.id))
            .where(Socio.activo.is_(True))
            .scalar_subquery(),
            socios_vencidos_sq,
            multas_sq,
        )
    ).one()
    return {
        "total_libros": fila[0],
        "total_ejemplares": fila[1],
        "total_prestados": fila[2],
        "socios_activos": fila[3],
        "socios_vencidos": fila[4],
        "multas_totales": fila[5] * TASA_MULTA_DIARIA if fila[5] else Decimal("0"),
    }
