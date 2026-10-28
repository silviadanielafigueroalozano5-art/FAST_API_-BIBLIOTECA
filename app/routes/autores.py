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
from app.core.database import get_db
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

router = APIRouter(prefix="/autores", tags=["Autores"])
libros_router = APIRouter(prefix="/libros", tags=["Libros"])
categorias_router = APIRouter(prefix="/categorias", tags=["Categorias"])


class OrdenLibro(str, Enum):
    """Valores válidos para ?orden= (el '-' significa descendente)."""

    titulo = "titulo"
    titulo_desc = "-titulo"
    anio = "anio"
    anio_desc = "-anio"


# ---------- AUTORES ----------


# CREAR (POST /autores)
@router.post("", response_model=AutorResponse, status_code=status.HTTP_201_CREATED)
def ruta_crear_autor(datos: AutorCrear, db: Session = Depends(get_db)):
    return crear_autor(db, datos)


# LISTAR (GET /autores) — paginado con skip/limit + filtro ?nacionalidad=
@router.get("", response_model=list[AutorResponse])
def ruta_listar_autores(
    nacionalidad: str | None = None,
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    return listar_autores(db, pag["skip"], pag["limit"], nacionalidad)


# OBTENER UNO (GET /autores/{autor_id})
@router.get("/{autor_id}", response_model=AutorResponse)
def ruta_obtener_autor(autor_id: int, db: Session = Depends(get_db)):
    return obtener_autor(db, autor_id)


# LIBROS DE UN AUTOR (GET /autores/{autor_id}/libros)
@router.get("/{autor_id}/libros", response_model=list[LibroResponse])
def ruta_libros_de_autor(
    autor_id: int,
    pag: dict = Depends(paginacion),
    db: Session = Depends(get_db),
):
    """Devuelve el autor con todos sus libros paginados."""
    _, libros = libros_de_autor(db, autor_id, pag["skip"], pag["limit"])
    return libros


# ACTUALIZAR (PATCH /autores/{autor_id})
@router.patch("/{autor_id}", response_model=AutorResponse)
def ruta_actualizar_autor(autor_id: int, datos: AutorUpdate, db: Session = Depends(get_db)):
    return actualizar_autor(db, autor_id, datos)


# ELIMINAR (DELETE /autores/{autor_id})
@router.delete("/{autor_id}", status_code=status.HTTP_204_NO_CONTENT)
def ruta_eliminar_autor(autor_id: int, db: Session = Depends(get_db)):
    eliminar_autor(db, autor_id)
    return None


# ---------- LIBROS ----------


# CREAR (POST /libros)
@libros_router.post("", response_model=LibroResponse, status_code=status.HTTP_201_CREATED)
def ruta_crear_libro(datos: LibroCrear, db: Session = Depends(get_db)):
    return crear_libro(db, datos)


# LISTAR (GET /libros) — paginado + FILTROS COMBINABLES (incluye JOIN con autores) + ORDEN
@libros_router.get("")
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
    return listar_libros(
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


# OBTENER UNO (GET /libros/{libro_id}) — incluye campo calculado 'disponibles'
@libros_router.get("/{libro_id}", response_model=LibroDetalle)
def ruta_obtener_libro(libro_id: int, db: Session = Depends(get_db)):
    return detalle_libro(db, libro_id)


# ACTUALIZAR (PATCH /libros/{libro_id})
@libros_router.patch("/{libro_id}", response_model=LibroResponse)
def ruta_actualizar_libro(libro_id: int, datos: LibroUpdate, db: Session = Depends(get_db)):
    return actualizar_libro(db, libro_id, datos)


# ELIMINAR (DELETE /libros/{libro_id})
@libros_router.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT)
def ruta_eliminar_libro(libro_id: int, db: Session = Depends(get_db)):
    eliminar_libro(db, libro_id)
    return None


# ---------- CATEGORÍAS ----------


# CREAR (POST /categorias) — 409 si ya existe
@categorias_router.post("", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
def ruta_crear_categoria(datos: CategoriaCrear, db: Session = Depends(get_db)):
    return crear_categoria(db, datos)


# LISTAR (GET /categorias)
@categorias_router.get("", response_model=list[CategoriaResponse])
def ruta_listar_categorias(pag: dict = Depends(paginacion), db: Session = Depends(get_db)):
    return listar_categorias(db, pag["skip"], pag["limit"])


# CONSULTAR UNA (GET /categorias/{categoria_id})
@categorias_router.get("/{categoria_id}", response_model=CategoriaResponse)
def ruta_obtener_categoria(categoria_id: int, db: Session = Depends(get_db)):
    return obtener_categoria(db, categoria_id)


# ACTUALIZAR (PATCH /categorias/{categoria_id})
@categorias_router.patch("/{categoria_id}", response_model=CategoriaResponse)
def ruta_actualizar_categoria(
    categoria_id: int, datos: CategoriaUpdate, db: Session = Depends(get_db)
):
    return actualizar_categoria(db, categoria_id, datos)


# ELIMINAR (DELETE /categorias/{categoria_id}) — se quita de los libros
@categorias_router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def ruta_eliminar_categoria(categoria_id: int, db: Session = Depends(get_db)):
    eliminar_categoria(db, categoria_id)
    return None
