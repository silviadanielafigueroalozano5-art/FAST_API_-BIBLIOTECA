"""Importa los modelos para registrarlos en metadata y Alembic."""

from app.models.autor import Autor, Libro
from app.models.categoria import Categoria
from app.models.prestamo import Prestamo
from app.models.refresh_token import RefreshToken
from app.models.socio import Socio
from app.models.usuario import RolUsuario, Usuario

__all__ = [
    "Autor",
    "Categoria",
    "Libro",
    "Prestamo",
    "RefreshToken",
    "RolUsuario",
    "Socio",
    "Usuario",
]