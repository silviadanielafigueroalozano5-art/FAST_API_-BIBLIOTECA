"""MODELO - Tabla autores y libros.

- `Autor`: los autores de la biblioteca.
- `Libro`: los libros, con LLAVE FORÁNEA hacia `autores`.
"""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.categoria import libro_categoria  # noqa: F401 (registro N:M)

from app.core.database import Base


class Autor(Base):
    __tablename__ = "autores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    nacionalidad: Mapped[str] = mapped_column(String(60), nullable=True)
    anio_nacimiento: Mapped[int] = mapped_column(nullable=True)

    # Relación 1 a muchos: un autor tiene muchos libros
    libros: Mapped[list["Libro"]] = relationship(back_populates="autor")


class Libro(Base):
    __tablename__ = "libros"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    # 13 dígitos, único en toda la tabla
    isbn: Mapped[str] = mapped_column(String(13), nullable=False, unique=True)
    anio_publicacion: Mapped[int] = mapped_column(nullable=False)
    ejemplares: Mapped[int] = mapped_column(nullable=False, default=1)
    # Enlace de Cloudinary con la imagen/portada del libro (opcional)
    imagen_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # LLAVE FORÁNEA: cada libro pertenece a un autor
    autor_id: Mapped[int] = mapped_column(ForeignKey("autores.id"), nullable=False)

    # Lado "muchos" de la relación
    autor: Mapped["Autor"] = relationship(back_populates="libros")

    # N:M: un libro puede tener varias categorías
    categorias: Mapped[list["Categoria"]] = relationship(
        back_populates="libros", secondary=libro_categoria
    )
