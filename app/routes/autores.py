"""ROUTES - Autores y Libros.

Las rutas reciben la petición HTTP, validan con los esquemas Pydantic
y llaman al controlador (app/controllers/autores_libros.py), que hace
las consultas y aplica las reglas de negocio.
"""
from enum import Enum

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers.autores_libros import (
    actualizar_autor,
    actualizar_libro,
    crear_autor,
    crear_libro,
    detalle_libro,
    eliminar_autor,
    eliminar_libro,
    listar_autores,
    listar_libros,
    libros_de_autor,
    obtener_autor,
    obtener_libro,
)
from app.controllers.categorias import (
    actualizar_categoria,
    crear_categoria,
    eliminar_categoria,
    listar_categorias,
    obtener_categoria,
)
from app.core.dependencies import Admin, Staff
from app.core.database import get_db
from app.core.openapi import RESPUESTAS_COMUNES
from app.core.paginacion import paginacion
from app.schemas.autor import (
    AutorCrear,
    AutorResponse,
    AutorUpdate,
    LibroCrear,
    LibroDetalle,
    LibroResponse,
    LibroUpdate,
)
from app.schemas.categoria import CategoriaCrear, CategoriaResponse, CategoriaUpdate
from app.schemas.pagina import Pagina

router = APIRouter(
    prefix="/autores", tags=["Autores"], responses=RESPUESTAS_COMUNES
)
libros_router = APIRouter(
    prefix="/libros", tags=["Libros"], responses=RESPUESTAS_COMUNES
)
categorias_router = APIRouter(
    prefix="/categorias", tags=["Categorías"], responses=RESPUESTAS_COMUNES
)


class OrdenLibro(str, Enum):
    """Valores válidos para ?orden= (el '-' significa descendente)."""

    titulo = "titulo"
    titulo_desc = "-titulo"
    anio = "anio"
    anio_desc = "-anio"


# ---------- AUTORES ----------


# CREAR (POST /autores)
@router.post(
    "",
    response_model=AutorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear autor",
    responses={401: {"description": "No autenticado"}, 403: {"description": "Permiso insuficiente"}},
)
def ruta_crear_autor(datos: AutorCrear, _: Staff, db: Session = Depends(get_db)):
    return crear_autor(db, datos)


# LISTAR (GET /autores) — paginado con skip/limit + filtro ?nacionalidad=
@router.get("", response_model=Pagina[AutorResponse], summary="Listar autores")
def ruta_listar_autores(
    nacionalidad: str | None = None,
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    items, total = listar_autores(db, pag["skip"], pag["limit"], nacionalidad)
    return {"items": items, "total": total, **pag}


# OBTENER UNO (GET /autores/{autor_id})
@router.get("/{autor_id}", response_model=AutorResponse, summary="Consultar autor")
def ruta_obtener_autor(autor_id: int, db: Session = Depends(get_db)):
    return obtener_autor(db, autor_id)


# LIBROS DE UN AUTOR (GET /autores/{autor_id}/libros)
@router.get("/{autor_id}/libros", response_model=Pagina[LibroResponse], summary="Consultar libros de un autor")
def ruta_libros_de_autor(
    autor_id: int,
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    """Devuelve el autor con todos sus libros paginados."""
    _, libros, total = libros_de_autor(db, autor_id, pag["skip"], pag["limit"])
    return {"items": libros, "total": total, **pag}


# ACTUALIZAR (PATCH /autores/{autor_id})
@router.patch("/{autor_id}", response_model=AutorResponse, summary="Actualizar autor")
def ruta_actualizar_autor(
    autor_id: int, datos: AutorUpdate, _: Staff, db: Session = Depends(get_db)
):
    return actualizar_autor(db, autor_id, datos)


# ELIMINAR (DELETE /autores/{autor_id})
@router.delete("/{autor_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar autor")
def ruta_eliminar_autor(autor_id: int, _: Admin, db: Session = Depends(get_db)):
    eliminar_autor(db, autor_id)
    return None


# ---------- LIBROS ----------


# CREAR (POST /libros)
@libros_router.post(
    "",
    response_model=LibroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear libro",
)
def ruta_crear_libro(datos: LibroCrear, _: Staff, db: Session = Depends(get_db)):
    return crear_libro(db, datos)


# LISTAR (GET /libros) — paginado + FILTROS COMBINABLES (incluye JOIN con autores) + ORDEN
@libros_router.get("", response_model=Pagina[LibroResponse], summary="Listar libros")
def ruta_listar_libros(
    buscar: str | None = Query(default=None, max_length=150, description="Búsqueda parcial por título"),
    titulo: str | None = Query(default=None, max_length=150, description="Alias de buscar"),
    autor_id: int | None = Query(default=None, gt=0, description="Filtra por autor"),
    categoria_id: int | None = Query(default=None, gt=0, description="Filtra por categoría (N:M)"),
    desde: int | None = Query(default=None, ge=1450, description="Año de publicación mínimo"),
    hasta: int | None = Query(default=None, le=2100, description="Año de publicación máximo"),
    anio_desde: int | None = Query(default=None, ge=1450, description="Alias de desde"),
    anio_hasta: int | None = Query(default=None, le=2100, description="Alias de hasta"),
    disponibles: bool | None = Query(default=None, description="Solo libros con ejemplares libres"),
    autor: str | None = Query(default=None, max_length=100, description="Búsqueda parcial por nombre del autor (JOIN)"),
    orden: OrdenLibro | None = Query(default=None, description="titulo | -titulo | anio | -anio"),
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    items, total = listar_libros(
        db,
        pag["skip"],
        pag["limit"],
        titulo=buscar or titulo,
        autor_id=autor_id,
        categoria_id=categoria_id,
        anio_desde=desde if desde is not None else anio_desde,
        anio_hasta=hasta if hasta is not None else anio_hasta,
        disponibles=disponibles,
        nombre_autor=autor,
        orden=orden.value if orden else None,
    )
    return {"items": items, "total": total, **pag}


# OBTENER UNO (GET /libros/{libro_id}) — incluye campo calculado 'disponibles'
@libros_router.get("/{libro_id}", response_model=LibroDetalle, summary="Consultar libro")
def ruta_obtener_libro(libro_id: int, db: Session = Depends(get_db)):
    return detalle_libro(db, libro_id)


# ACTUALIZAR (PATCH /libros/{libro_id})
@libros_router.patch("/{libro_id}", response_model=LibroResponse, summary="Actualizar libro")
def ruta_actualizar_libro(
    libro_id: int, datos: LibroUpdate, _: Staff, db: Session = Depends(get_db)
):
    return actualizar_libro(db, libro_id, datos)


# ELIMINAR (DELETE /libros/{libro_id})
@libros_router.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar libro")
def ruta_eliminar_libro(libro_id: int, _: Admin, db: Session = Depends(get_db)):
    eliminar_libro(db, libro_id)
    return None


# ---------- CATEGORÍAS ----------


# CREAR (POST /categorias) — 409 si ya existe
@categorias_router.post(
    "", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED,
    summary="Crear categoría",
)
def ruta_crear_categoria(datos: CategoriaCrear, _: Staff, db: Session = Depends(get_db)):
    return crear_categoria(db, datos)


# LISTAR (GET /categorias)
@categorias_router.get("", response_model=Pagina[CategoriaResponse], summary="Listar categorías")
def ruta_listar_categorias(pag: dict = Depends(paginacion), db: Session = Depends(get_db)):
    items, total = listar_categorias(db, pag["skip"], pag["limit"])
    return {"items": items, "total": total, **pag}


# CONSULTAR UNA (GET /categorias/{categoria_id})
@categorias_router.get("/{categoria_id}", response_model=CategoriaResponse, summary="Consultar categoría")
def ruta_obtener_categoria(categoria_id: int, db: Session = Depends(get_db)):
    return obtener_categoria(db, categoria_id)


# ACTUALIZAR (PATCH /categorias/{categoria_id})
@categorias_router.patch("/{categoria_id}", response_model=CategoriaResponse, summary="Actualizar categoría")
def ruta_actualizar_categoria(
    categoria_id: int, datos: CategoriaUpdate, _: Staff, db: Session = Depends(get_db)
):
    return actualizar_categoria(db, categoria_id, datos)


# ELIMINAR (DELETE /categorias/{categoria_id}) — se quita de los libros
@categorias_router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar categoría")
def ruta_eliminar_categoria(categoria_id: int, _: Admin, db: Session = Depends(get_db)):
    eliminar_categoria(db, categoria_id)
    return None
