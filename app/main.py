"""Punto de entrada de la API (une todo el MVC).

- Importa los routers del CONTROLADOR.
- Crea la app FastAPI (la VISTA de respuestas la generan los schemas).
- Crea las tablas en PostgreSQL a partir de los MODELOS.
"""
from fastapi import FastAPI

import app.models.autor  # noqa: F401  (necesario para que SQLAlchemy registre las tablas)
import app.models.socio  # noqa: F401  (registra la tabla socios)
import app.models.prestamo  # noqa: F401  (registra la tabla prestamos)
from app.core.exceptions import ErrorAplicacion, app_error_handler
from app.core.database import Base, engine
from app.routes.autores import (
    categorias_router,
    libros_router,
    router as autores_router,
)
from app.routes.prestamos import prestamos_router
from app.routes.socios import socios_router
from app.routes.reportes import reportes_router

app = FastAPI(
    title="API de Biblioteca",
    description="Gestión de libros y autores con FastAPI + PostgreSQL (MVC)",
    version="2.0",
)

# ÚNICO exception_handler: convierte las excepciones propias de
# core/exceptions.py en {"detail": "mensaje"}
app.add_exception_handler(ErrorAplicacion, app_error_handler)

# Creamos el esquema: genera las tablas autores y libros (con la FK) en PostgreSQL
Base.metadata.create_all(bind=engine)
print("Tablas 'autores' y 'libros' creadas o verificadas exitosamente")

app.include_router(autores_router)
app.include_router(libros_router)
app.include_router(categorias_router)
app.include_router(socios_router)
app.include_router(prestamos_router)
app.include_router(reportes_router)
