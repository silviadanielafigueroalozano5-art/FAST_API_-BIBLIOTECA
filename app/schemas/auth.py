"""Esquemas de registro, autenticación y administración de usuarios."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.usuario import RolUsuario

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,64}$")


class UsuarioRegistro(BaseModel):
    email: EmailStr = Field(max_length=150)
    nombre: str = Field(min_length=3, max_length=100)
    telefono: str | None = Field(default=None, min_length=7, max_length=15)
    password: str = Field(min_length=8, max_length=64)
    confirmar_password: str = Field(min_length=8, max_length=64)

    @field_validator("email", mode="after")
    @classmethod
    def email_minusculas(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("nombre", mode="before")
    @classmethod
    def limpiar_nombre(cls, value: object) -> object:
        return value.strip().title() if isinstance(value, str) else value

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"^[+\d][\d\s]{6,14}$", value.strip()):
            raise ValueError("El teléfono solo puede contener dígitos, espacios y '+'")
        return value.strip() if value else value

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str) -> str:
        if not PASSWORD_RE.fullmatch(value):
            raise ValueError(
                "La contraseña debe tener entre 8 y 64 caracteres, "
                "una mayúscula, una minúscula y un número"
            )
        return value

    @model_validator(mode="after")
    def confirmar_password_coincide(self):
        if self.password != self.confirmar_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class UsuarioRespuesta(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    rol: RolUsuario
    activo: bool
    socio_id: int | None
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenRespuesta(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=64)

    @field_validator("password_nueva")
    @classmethod
    def validar_password(cls, value: str) -> str:
        if not PASSWORD_RE.fullmatch(value):
            raise ValueError(
                "La contraseña debe tener entre 8 y 64 caracteres, "
                "una mayúscula, una minúscula y un número"
            )
        return value


class UsuarioCrear(BaseModel):
    email: EmailStr = Field(max_length=150)
    nombre: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=64)
    rol: RolUsuario

    @field_validator("email", mode="after")
    @classmethod
    def email_minusculas(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("nombre", mode="before")
    @classmethod
    def normalizar_nombre(cls, value: object) -> object:
        return value.strip().title() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str) -> str:
        if not PASSWORD_RE.fullmatch(value):
            raise ValueError(
                "La contraseña debe tener entre 8 y 64 caracteres, "
                "una mayúscula, una minúscula y un número"
            )
        return value

    @model_validator(mode="after")
    def no_crear_socio_desde_admin(self):
        if self.rol == RolUsuario.socio:
            raise ValueError("Los socios deben registrarse desde /auth/registro")
        return self


class RolUpdate(BaseModel):
    rol: RolUsuario


class ActivoUpdate(BaseModel):
    activo: bool
