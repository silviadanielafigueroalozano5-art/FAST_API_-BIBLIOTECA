"""MODELO - Tabla categorias.

Cada categoría puede estar asignada a muchos libros (relación N:M).
"""
from sqlalchemy import String, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Tabla intermedia (N:M) entre libros y categorías
libro_categoria = Table(
    "libro_categoria",
    Base.metadata,
    Column("libro_id", ForeignKey("libros.id"), primary_key=True),
    Column("categoria_id", ForeignKey("categorias.id"), primary_key=True),
)


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Lado "muchos" de la relación N:M
    libros: Mapped[list["Libro"]] = relationship(
        back_populates="categorias", secondary=libro_categoria
    )
