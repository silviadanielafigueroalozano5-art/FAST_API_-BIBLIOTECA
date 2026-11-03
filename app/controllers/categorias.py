
"""CONTROLLER - Lógica de negocio de Categorías.

Los controladores hacen las consultas (SQLAlchemy), aplican las reglas
de negocio y lanzan las excepciones propias de core/exceptions.py.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import Conflicto, NoEncontrado
from app.models.categoria import Categoria


def crear_categoria(db: Session, datos) -> Categoria:
    if db.scalar(select(Categoria).where(Categoria.nombre == datos.nombre)):
        raise Conflicto(f"Ya existe la categoría '{datos.nombre}'")
    categoria = Categoria(**datos.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def listar_categorias(
    db: Session, skip: int = 0, limit: int = 20
) -> tuple[list[Categoria], int]:
    consulta = select(Categoria)
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    items = list(db.scalars(consulta.offset(skip).limit(limit)).all())
    return items, total


def obtener_categoria(db: Session, categoria_id: int) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if not categoria:
        raise NoEncontrado(f"Categoría con id={categoria_id} no encontrada")
    return categoria


def actualizar_categoria(db: Session, categoria_id: int, datos) -> Categoria:
    categoria = obtener_categoria(db, categoria_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"] != categoria.nombre:
        if db.scalar(select(Categoria).where(Categoria.nombre == cambios["nombre"])):
            raise Conflicto(f"Ya existe la categoría '{cambios['nombre']}'")
    for campo, valor in cambios.items():
        setattr(categoria, campo, valor)
    db.commit()
    db.refresh(categoria)
    return categoria


def eliminar_categoria(db: Session, categoria_id: int) -> None:
    categoria = obtener_categoria(db, categoria_id)
    # Regla: se quita la categoría de los libros que la tenían
    for libro in list(categoria.libros):
        libro.categorias.remove(categoria)
    db.delete(categoria)
    db.commit()
