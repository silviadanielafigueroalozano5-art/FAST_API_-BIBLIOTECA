"""Respuestas compartidas para describir la autenticación y errores de recursos."""

RESPUESTAS_COMUNES = {
    401: {"description": "Autenticación requerida o token inválido"},
    403: {"description": "El usuario autenticado no tiene permiso"},
    404: {"description": "El recurso no existe o no pertenece al usuario"},
}
