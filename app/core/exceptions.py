"""CORE - Excepciones propias del dominio.

Cada excepción sabe qué código HTTP le corresponde. En main.py un
único exception_handler las convierte en {"detail": "mensaje"}.

| Excepción       | Código | Cuándo se usa                                         |
|-----------------|--------|--------------------------------------------------------|
| ErrorAplicacion | 400    | Clase base de todas las excepciones propias            |
| NoEncontrado    | 404    | El recurso no existe                                   |
| Conflicto       | 409    | Datos duplicados o borrar algo con datos dependientes  |
| ReglaNegocio    | 422    | Una regla de la biblioteca no se cumple                |
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse


class ErrorAplicacion(Exception):
    """Clase BASE de todas las excepciones propias. Responde 400 por defecto."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    mensaje: str = "Error en la aplicación"

    def __init__(self, mensaje: str | None = None) -> None:
        if mensaje:
            self.mensaje = mensaje
        super().__init__(self.mensaje)


class NoEncontrado(ErrorAplicacion):
    """404 - El recurso buscado no existe."""

    status_code = status.HTTP_404_NOT_FOUND
    mensaje = "Recurso no encontrado"


class Conflicto(ErrorAplicacion):
    """409 - Datos duplicados o borrar algo que tiene datos dependientes."""

    status_code = status.HTTP_409_CONFLICT
    mensaje = "Conflicto con el estado actual del recurso"


class ReglaNegocio(ErrorAplicacion):
    """422 - Una regla de la biblioteca no se cumple."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    mensaje = "Regla de negocio incumplida"


def app_error_handler(request: Request, exc: ErrorAplicacion) -> JSONResponse:
    """ÚNICO handler: convierte cualquier AppError en {"detail": "mensaje"}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.mensaje},
    )
