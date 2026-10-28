"""Esquemas de validación (Pydantic) para socios (Fase 4B).

- `email`: `EmailStr` (valida formato), se guarda en minúsculas y es
  único (lo fuerza el controlador).
- `telefono`: opcional, 7-15 caracteres, solo dígitos, espacios y '+'.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

TELEFONO_RE = re.compile(r"^[+\d][\d\s]{6,14}$")


class SocioBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=100, examples=["Ana Gómez"])
    email: EmailStr = Field(examples=["ana@correo.com"])
    telefono: str | None = Field(
        default=None,
        min_length=7,
        max_length=15,
        description="Solo dígitos, espacios y '+'",
        examples=["+34 600 123 456"],
    )

    @field_validator("nombre", "email", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("email")
    @classmethod
    def email_en_minusculas(cls, valor: EmailStr) -> str:
        """Regla: el email se guarda SIEMPRE en minúsculas."""
        return str(valor).lower()

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, valor: str | None) -> str | None:
        if valor is None:
            return valor
        valor = valor.strip()
        if not TELEFONO_RE.fullmatch(valor):
            raise ValueError(
                "El teléfono solo puede contener dígitos, espacios y '+', de 7 a 15 caracteres"
            )
        return valor


class SocioCrear(SocioBase):
    pass


class SocioUpdate(BaseModel):
    """PATCH de socio: solo se actualizan los campos enviados."""

    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, min_length=7, max_length=15)

    @field_validator("nombre", "email", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("email")
    @classmethod
    def email_en_minusculas(cls, valor: EmailStr | None) -> str | None:
        return str(valor).lower() if valor else valor

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, valor: str | None) -> str | None:
        if valor is None:
            return valor
        valor = valor.strip()
        if not TELEFONO_RE.fullmatch(valor):
            raise ValueError(
                "El teléfono solo puede contener dígitos, espacios y '+', de 7 a 15 caracteres"
            )
        return valor


class SocioResponse(SocioBase):
    id: int
    activo: bool
    # La genera la BD (server_default)
    fecha_alta: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
