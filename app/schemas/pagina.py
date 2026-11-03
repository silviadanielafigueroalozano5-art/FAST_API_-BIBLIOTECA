"""Formato uniforme para las respuestas de listados paginados."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
