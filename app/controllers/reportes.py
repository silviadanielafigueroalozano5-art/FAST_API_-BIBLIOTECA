"""CONTROLLER - Reportes con agregados y totales paginados.

Los agregados (COUNT, SUM) se calculan en PostgreSQL, no en Python;
- LEFT JOIN para no perder filas (categorías sin libros, autores sin
  préstamos, etc.);
- COALESCE para mostrar 0 en vez de NULL en los conteos;
- los totales de paginación se consultan con COUNT en la base de datos.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.autor import Autor, Libro
from app.models.categoria import Categoria, libro_categoria
from app.models.prestamo import Prestamo
from app.models.socio import Socio

TASA_MULTA_DIARIA = Decimal(get_settings().tasa_multa_diaria)


def libros_mas_prestados(
    db: Session, limit: int = 10, skip: int = 0
) -> tuple[list[dict], int]:
    """Top de libros por nº de préstamos (incluye devueltos).

    Consulta agrupada: JOIN libros+autores y COUNT de préstamos.
    """
    total = db.scalar(select(func.count(Libro.id))) or 0
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
        .offset(skip)
        .limit(limit)
    ).all()
    items = [
        {
            "libro_id": lid,
            "titulo": titulo,
            "autor": autor,
            "total_prestamos": total_prestamos,
        }
        for lid, titulo, autor, total_prestamos in filas
    ]
    return items, total


def libros_por_categoria(
    db: Session, skip: int = 0, limit: int = 10
) -> tuple[list[dict], int]:
    """Nº de libros por categoría con LEFT JOIN para incluir los ceros.
    """
    total = db.scalar(select(func.count(Categoria.id))) or 0
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
        .offset(skip)
        .limit(limit)
    ).all()
    items = [
        {"categoria_id": cid, "categoria": nombre, "total_libros": total_libros}
        for cid, nombre, total_libros in filas
    ]
    return items, total


def prestamos_vencidos(
    db: Session, skip: int = 0, limit: int = 10
) -> tuple[list[dict], int]:
    """Préstamos sin devolver con fecha_limite pasada, ordenados por
    retraso descendente. El retraso se calcula en SQL con
    CURRENT_DATE - fecha_limite.
    """
    filtros = (
        Prestamo.fecha_devolucion.is_(None),
        Prestamo.fecha_limite < date.today(),
    )
    total = db.scalar(
        select(func.count(Prestamo.id)).where(*filtros)
    ) or 0
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
        .where(*filtros)
        .order_by(Prestamo.fecha_limite)
        .offset(skip)
        .limit(limit)
    ).all()
    items = [
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
    return items, total


def socios_con_multas(
    db: Session, skip: int = 0, limit: int = 10
) -> tuple[list[dict], int]:
    """Socios con multa PENDIENTE > 0, ordenados por multa descendente.

    Multa pendiente = multas impagas (devueltos con multa_pagada=False)
    + retraso de vencidos sin devolver. Usa dos
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
    dias_retraso = cast(hoy - Prestamo.fecha_limite, Integer)
    retraso_sq = (
        select(
            Prestamo.socio_id,
            func.sum(
                case((dias_retraso > 0, dias_retraso), else_=0)
            ).label("dias"),
            func.count(Prestamo.id).label("vencidos"),
        )
        .where(Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < hoy)
        .group_by(Prestamo.socio_id)
        .subquery()
    )
    consulta = (
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
    )
    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    filas = db.execute(consulta.offset(skip).limit(limit)).all()
    items = [
        {
            "socio_id": sid,
            "nombre": nombre,
            "email": email,
            "multa_total": multa or Decimal("0"),
            "prestamos_vencidos": vencidos,
        }
        for sid, nombre, email, multa, vencidos in filas
    ]
    return items, total


def reporte_autores(
    db: Session, skip: int = 0, limit: int = 10
) -> tuple[list[dict], int]:
    """Por autor: nº de libros escritos y nº de préstamos totales.

    Usa 2 LEFT JOIN y COUNT(DISTINCT) para no duplicar
    (un libro puede tener varios préstamos; un autor varios libros).
    """
    total = db.scalar(select(func.count(Autor.id))) or 0
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
        .offset(skip)
        .limit(limit)
    ).all()
    items = [
        {
            "autor_id": aid,
            "autor": nombre,
            "total_libros": libros,
            "total_prestamos": prestamos,
        }
        for aid, nombre, libros, prestamos in filas
    ]
    return items, total


def resumen(db: Session) -> dict:
    """Totales generales en UNA consulta (subconsultas escalares)."""
    dias_retraso = cast(date.today() - Prestamo.fecha_limite, Integer)
    total_prestados_sq = (
        select(func.count(Prestamo.id))
        .where(Prestamo.fecha_devolucion.is_(None))
        .scalar_subquery()
    )
    multas_sq = (
        select(
            func.coalesce(
                func.sum(
                    case((dias_retraso > 0, dias_retraso), else_=0)
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
