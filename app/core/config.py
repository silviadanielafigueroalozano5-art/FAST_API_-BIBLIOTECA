"""Configuración tipada cargada desde el entorno y el archivo .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Formato completo: DATABASE_URL=postgresql+psycopg://user:pass@host:port/db
    database_url: str | None = None
    test_database_url: str | None = None

    # Alternativa por partes (como en el .env actual del proyecto)
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "biblioteca"

    secret_key: SecretStr = Field(min_length=32)
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    cors_origins: list[str] = Field(default_factory=list)
    environment: Literal["dev", "test", "prod"] = "dev"
    tasa_multa_diaria: str = "0.50"

    # Cloudinary (para subir imágenes de portadas de libros)
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: SecretStr | None = None

    @property
    def cloudinary_activa(self) -> bool:
        return bool(
            self.cloudinary_cloud_name
            and self.cloudinary_api_key
            and self.cloudinary_api_secret
            and self.cloudinary_api_secret.get_secret_value()
        )

    @property
    def database_url_efectiva(self) -> str:
        """Normaliza DATABASE_URL o la arma desde DB_HOST/DB_PORT/..."""
        if self.database_url:
            if self.database_url.startswith("postgres://"):
                return self.database_url.replace(
                    "postgres://", "postgresql+psycopg://", 1
                )
            if self.database_url.startswith("postgresql://"):
                return self.database_url.replace(
                    "postgresql://", "postgresql+psycopg://", 1
                )
            return self.database_url
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @model_validator(mode="after")
    def validar_cors_produccion(self):
        if self.environment == "prod" and "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS no puede contener '*' en producción")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
