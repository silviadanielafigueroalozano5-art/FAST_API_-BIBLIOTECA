"""MODELO - Tabla socios (Fase 4B).

Un socio es la persona que puede pedir libros prestados. Usa BORRADO
LÓGICO: si tiene historial de préstamos no se elimina, se marca
`activo=False` para conservar la integridad del historial.
"""

from datetime import datetime
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Socio(Base):
    __tablename__ = "socios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    # ÚNICO y siempre en minúsculas (lo fuerza el schema)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    # Opcional: 7 a 15 caracteres, solo dígitos, espacios y '+'
    telefono: Mapped[str | None] = mapped_column(String(15), nullable=True)
    # Por defecto True; False = borrado lógico (tiene historial)
    activo: Mapped[bool] = mapped_column(default=True)
    # La genera la base de datos al insertar
    fecha_alta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prestamos: Mapped[list["Prestamo"]] = relationship(back_populates="socio")
    usuario: Mapped["Usuario | None"] = relationship(back_populates="socio", uselist=False)
