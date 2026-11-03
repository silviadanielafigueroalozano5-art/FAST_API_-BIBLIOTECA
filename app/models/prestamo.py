"""MODELO - Tabla prestamos (Fase 5).

Un préstamo registra que un libro salió de la biblioteca:
- FK a `libros` (qué libro se prestó)
- FK a `socios` (a quién se prestó — el modelo vive en app/models/socio.py)
- fechas: préstamo, LÍMITE de devolución y devolución real
- `multa`: decimal que se calcula al registrar la devolución

El ESTADO NO SE GUARDA: se calcula a partir de las fechas
(app/controllers/prestamos.py):
- devuelto -> fecha_devolucion tiene valor
- vencido  -> no devuelto y fecha_limite anterior a hoy
- activo   -> no devuelto y fecha_limite igual o posterior a hoy
"""
from datetime import date
from decimal import Decimal
from sqlalchemy import Boolean, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(primary_key=True)
    libro_id: Mapped[int] = mapped_column(ForeignKey("libros.id"), nullable=False)
    socio_id: Mapped[int] = mapped_column(ForeignKey("socios.id"), nullable=False)

    fecha_prestamo: Mapped[date] = mapped_column(Date, nullable=False)
    # fecha_prestamo + dias (regla del negocio: entre 1 y 30, por defecto 14)
    fecha_limite: Mapped[date] = mapped_column(Date, nullable=False)
    # None mientras el libro no se devuelva
    fecha_devolucion: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Por defecto 0; se calcula al devolver (días de retraso × tasa)
    multa: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # False hasta que el socio la pague (la multa devuelta con retraso
    # cuenta como PENDIENTE para las reglas de préstamo)
    multa_pagada: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="false"
    )
    registrado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    # Relaciones inversas
    libro: Mapped["Libro"] = relationship()
    socio: Mapped["Socio"] = relationship(back_populates="prestamos")
