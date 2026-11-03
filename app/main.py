"""Aplicación FastAPI: routers, seguridad transversal y errores."""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.exceptions import ErrorAplicacion, app_error_handler
from app.core.limiter import limiter
from app.routes.auth import router as auth_router
from app.routes.autores import (
    categorias_router,
    libros_router,
    router as autores_router,
)
from app.routes.health import router as health_router
from app.routes.prestamos import prestamos_router
from app.routes.reportes import reportes_router
from app.routes.socios import socios_router
from app.routes.usuarios import router as usuarios_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("biblioteca.api")
settings = get_settings()

app = FastAPI(
    title="API de Biblioteca",
    description="Gestión segura de biblioteca con autenticación JWT y roles.",
    version="3.0",
    docs_url=None if settings.environment == "prod" else "/docs",
    redoc_url=None if settings.environment == "prod" else "/redoc",
    openapi_url=None if settings.environment == "prod" else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(ErrorAplicacion, app_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def registrar_peticion(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    inicio = time.perf_counter()
    response = await call_next(request)
    duracion_ms = (time.perf_counter() - inicio) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s %s %.2fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duracion_ms,
        request_id,
    )
    return response


@app.exception_handler(Exception)
async def error_interno(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Error no controlado request_id=%s",
        request_id,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
        headers={"X-Request-ID": request_id},
    )


API_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(autores_router, prefix=API_PREFIX)
app.include_router(libros_router, prefix=API_PREFIX)
app.include_router(categorias_router, prefix=API_PREFIX)
app.include_router(socios_router, prefix=API_PREFIX)
app.include_router(prestamos_router, prefix=API_PREFIX)
app.include_router(reportes_router, prefix=API_PREFIX)
app.include_router(usuarios_router, prefix=API_PREFIX)
