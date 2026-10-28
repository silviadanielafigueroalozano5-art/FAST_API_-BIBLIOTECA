"""Esquemas de validación (Pydantic) para préstamos (Fase 5).

- `dias`: 1 a 30, POR DEFECTO 14. La fecha límite se calcula en el
  controller como fecha_prestamo + dias.
- `fecha_prestamo` no puede ser futura (regla R1, doble validación).
- El ESTADO no se guarda: `PrestamoResponse.estado` es un campo
  calculado con @computed_field a partir de las fechas.
- `multa` es decimal (se calcula al devolver).
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.autor import LibroResponse
from app.schemas.socio import SocioResponse

DIAS_MAX = 30
DIAS_DEFAULT = 14


class PrestamoCrear(BaseModel):
    # FKs: el cliente solo envía los IDs
    libro_id: int = Field(gt=0, examples=[1])
    socio_id: int = Field(gt=0, examples=[1])
    # Opcional: por defecto HOY (se puede enviar fecha pasada, nunca futura)
    fecha_prestamo: date | None = Field(default=None, examples=["2026-10-20"])
    # Regla R2: entre 1 y 30 días, por defecto 14
    dias: int = Field(
        default=DIAS_DEFAULT,
        ge=1,
        le=DIAS_MAX,
        description=f"Días del préstamo (1 a {DIAS_MAX}). Por defecto {DIAS_DEFAULT}",
        examples=[14],
    )

    @field_validator("fecha_prestamo")
    @classmethod
    def fecha_no_futura(cls, valor: date | None) -> date | None:
        """Regla R1: no se permiten préstamos a fecha futura."""
        if valor and valor > date.today():
            raise ValueError("La fecha de préstamo no puede ser futura")
        return valor


class PrestamoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    libro_id: int
    socio_id: int
    fecha_prestamo: date
    fecha_limite: date
    fecha_devolucion: date | None
    multa: Decimal
    multa_pagada: bool = True
    # Datos anidados del libro y del socio (salen de las relationships)
    libro: LibroResponse
    socio: SocioResponse

    @computed_field  # type: ignore[prop-decorator]
    @property
    def estado(self) -> str:
        """Estado CALCULADO a partir de las fechas (no se guarda en BD)."""
        if self.fecha_devolucion is not None:
            return "devuelto"
        return "vencido" if self.fecha_limite < date.today() else "activo"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dias_retraso(self) -> int:
        """Días de retraso respecto al límite (0 si no hay)."""
        referencia = self.fecha_devolucion or date.today()
        retraso = (referencia - self.fecha_limite).days
        return max(retraso, 0)


class PrestamoDevolucionIn(BaseModel):
    """Body opcional de la devolución: puede especificar la fecha.

    Si no se envía, se usa la fecha de hoy. No puede ser anterior a la
    del préstamo (lo valida el controller, R9b).
    """

    fecha_devolucion: date | None = Field(default=None, examples=["2026-11-03"])


class PrestamoDevolucion(BaseModel):
    """Respuesta al registrar la devolución."""

    id: int
    fecha_devolucion: date
    multa: Decimal
    estado: str = "devuelto"
    dias_retraso: int
    message: str = "Devolución registrada correctamente"
