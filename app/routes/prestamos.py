"""ROUTES - Préstamos (Fase 4).

Las rutas reciben la petición HTTP, validan con los esquemas Pydantic
y llaman al controlador (app/controllers/prestamos.py), que aplica las
reglas de negocio (disponibilidad del libro, socio activo, devoluciones).

Las rutas de socios viven en app/routes/socios.py.
"""
from fastapi import APIRouter, Depends, Query, status

from app.controllers.prestamos import (
    crear_prestamo,
    devolver_prestamo,
    listar_prestamos,
    obtener_prestamo,
    pagar_multa,
)
from app.core.dependencies import CurrentUser, SessionDep, Staff
from app.core.exceptions import NoEncontrado
from app.core.openapi import RESPUESTAS_COMUNES
from app.core.paginacion import paginacion
from app.schemas.prestamo import (
    PrestamoCrear,
    PrestamoDevolucion,
    PrestamoDevolucionIn,
    PrestamoResponse,
)
from app.schemas.pagina import Pagina
from app.models.usuario import RolUsuario

prestamos_router = APIRouter(
    prefix="/prestamos", tags=["Préstamos"], responses=RESPUESTAS_COMUNES
)


# CREAR PRÉSTAMO (POST /prestamos)
# Reglas: fecha no futura, dias 1-30 (default 14), socio activo,
# ejemplares libres, máximo 3 activos, sin multas pendientes.
@prestamos_router.post(
    "",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar préstamo",
)
def ruta_crear_prestamo(datos: PrestamoCrear, usuario: Staff, db: SessionDep):
    return crear_prestamo(db, datos, registrado_por_id=usuario.id)


# LISTAR (GET /prestamos) — paginado + FILTROS COMBINABLES
# ?estado=activo|vencido|devuelto  ?socio_id=  ?libro_id=
@prestamos_router.get(
    "", response_model=Pagina[PrestamoResponse], summary="Listar préstamos"
)
def ruta_listar_prestamos(
    usuario: CurrentUser,
    db: SessionDep,
    estado: str | None = Query(
        default=None, description="activo | vencido | devuelto"
    ),
    socio_id: int | None = Query(default=None, gt=0, description="Filtra por socio"),
    libro_id: int | None = Query(default=None, gt=0, description="Filtra por libro"),
    pag: dict = Depends(paginacion),
):
    if usuario.rol == RolUsuario.socio and usuario.socio_id is None:
        raise NoEncontrado("El usuario no tiene un perfil de socio")
    propio_socio_id = usuario.socio_id if usuario.rol == RolUsuario.socio else None
    items, total = listar_prestamos(
        db,
        pag["skip"],
        pag["limit"],
        estado=estado,
        socio_id=socio_id if propio_socio_id is None else None,
        libro_id=libro_id,
        propio_socio_id=propio_socio_id,
    )
    return {"items": items, "total": total, **pag}


# OBTENER UNO (GET /prestamos/{prestamo_id}) — incluye estado calculado y multa
@prestamos_router.get(
    "/{prestamo_id}",
    response_model=PrestamoResponse,
    summary="Consultar préstamo",
)
def ruta_obtener_prestamo(
    prestamo_id: int, usuario: CurrentUser, db: SessionDep
):
    prestamo = obtener_prestamo(db, prestamo_id)
    if usuario.rol == RolUsuario.socio and prestamo.socio_id != usuario.socio_id:
        raise NoEncontrado("Préstamo no encontrado")
    return prestamo


# REGISTRAR DEVOLUCIÓN (POST /prestamos/{prestamo_id}/devolucion)
# R9: 409 si ya devuelto; 422 si la fecha es anterior al préstamo.
# R10: multa = días de retraso × 0,50.
@prestamos_router.post(
    "/{prestamo_id}/devolucion",
    response_model=PrestamoDevolucion,
    status_code=status.HTTP_200_OK,
    summary="Registrar devolución",
)
def ruta_devolver_prestamo(
    prestamo_id: int,
    _: Staff,
    db: SessionDep,
    datos: PrestamoDevolucionIn | None = None,
):
    fecha = datos.fecha_devolucion if datos else None
    prestamo = devolver_prestamo(db, prestamo_id, fecha)
    retraso = (prestamo.fecha_devolucion - prestamo.fecha_limite).days
    return PrestamoDevolucion(
        id=prestamo.id,
        fecha_devolucion=prestamo.fecha_devolucion,
        multa=prestamo.multa,
        dias_retraso=max(retraso, 0),
    )


@prestamos_router.post(
    "/{prestamo_id}/pago-multa",
    response_model=PrestamoResponse,
    summary="Registrar pago de multa",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Permiso insuficiente"}, 404: {"description": "Préstamo no encontrado"}, 409: {"description": "Multa inexistente o ya pagada"}},
)
def ruta_pagar_multa(prestamo_id: int, _: Staff, db: SessionDep):
    return pagar_multa(db, prestamo_id)
