"""Esquemas de validación (Pydantic) para categorías."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoriaBase(BaseModel):
    nombre: str = Field(min_length=3, max_length=50, examples=["terror"])
    descripcion: str | None = Field(default=None, max_length=200)

    @field_validator("nombre", "descripcion", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        """Regla: quita espacios sobrantes."""
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("nombre")
    @classmethod
    def a_minusculas(cls, valor: str) -> str:
        """Regla: el nombre se guarda siempre en minúsculas."""
        return valor.lower()


class CategoriaCrear(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    """Para PATCH: solo se actualizan los campos enviados."""

    nombre: str | None = Field(default=None, min_length=3, max_length=50)
    descripcion: str | None = Field(default=None, max_length=200)

    @field_validator("nombre", "descripcion", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("nombre")
    @classmethod
    def a_minusculas(cls, valor: str) -> str:
        return valor.lower()


class CategoriaResponse(CategoriaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
