"""CORE - Conexión a la base de datos.

Crea el engine de SQLAlchemy y la fábrica de sesiones que
entregamos a cada petición vía get_db() (inyección de dependencias).
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import DATABASE_URL


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos (tablas)."""


engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, expire_on_commit=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión de BD a cada petición y la cierra al terminar."""
    with SessionLocal() as db:
        yield db
