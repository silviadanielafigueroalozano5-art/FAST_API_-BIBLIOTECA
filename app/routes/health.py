"""Comprobación de disponibilidad de la API y PostgreSQL."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
from app.core.openapi import RESPUESTAS_COMUNES

router = APIRouter(tags=["Salud"])


@router.get(
    "/health",
    summary="Comprobar el estado del servicio",
    responses={
        **RESPUESTAS_COMUNES,
        503: {"description": "La base de datos no responde"},
    },
)
def health() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "database": "ok"},
    )
