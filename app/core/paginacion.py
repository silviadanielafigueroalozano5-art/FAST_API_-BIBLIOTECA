"""DEPENDENCIA reutilizable de paginación.

Todas las rutas de listado la reciben con Depends(paginacion).
- skip: mínimo 0
- limit: entre 1 y 100
"""
from fastapi import Query


def paginacion(
    skip: int = Query(default=0, ge=0, description="Registros a saltar"),
    limit: int = Query(default=10, ge=1, le=100, description="Máximo de registros"),
) -> dict[str, int]:
    return {"skip": skip, "limit": limit}
