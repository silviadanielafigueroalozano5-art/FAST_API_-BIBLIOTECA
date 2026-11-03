"""CORE - Conexión a la base de datos.

Crea el engine de SQLAlchemy y la fábrica de sesiones que
entregamos a cada petición vía get_db() (inyección de dependencias).
"""
from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos (tablas)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def crear_engine(database_url: str) -> Engine:
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        return create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url, echo=False, pool_pre_ping=True)


settings = get_settings()
database_url = (
    settings.test_database_url
    if settings.environment == "test" and settings.test_database_url
    else settings.database_url
)
engine = crear_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, expire_on_commit=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión de BD a cada petición y la cierra al terminar."""
    with SessionLocal() as db:
        yield db
