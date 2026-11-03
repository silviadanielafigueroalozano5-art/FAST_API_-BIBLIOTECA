"""CONTROLLER - Lógica de negocio de Autores y Libros.

Los controladores hacen las consultas (SQLAlchemy), aplican las reglas
de negocio y lanzan las excepciones propias de core/exceptions.py.
Las rutas solo reciben la petición, validan con Pydantic y delegan aquí.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import Conflicto, NoEncontrado, ReglaNegocio
from app.models.autor import Autor, Libro
from app.models.categoria import Categoria
from app.models.prestamo import Prestamo


# ---------- AUTORES ----------


def crear_autor(db: Session, datos) -> Autor:
    if db.scalar(select(Autor).where(Autor.nombre == datos.nombre)):
        raise Conflicto(f"Ya existe un autor llamado '{datos.nombre}'")
    autor = Autor(**datos.model_dump())
    db.add(autor)
    db.commit()
    db.refresh(autor)
    return autor


def listar_autores(
    db: Session, skip: int = 0, limit: int = 20, nacionalidad: str | None = None
) -> tuple[list[Autor], int]:
    consulta = select(Autor)
    if nacionalidad:
        consulta = consulta.where(Autor.nacionalidad == nacionalidad)
    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    items = list(db.scalars(consulta.offset(skip).limit(limit)).all())
    return items, total


def obtener_autor(db: Session, autor_id: int) -> Autor:
    autor = db.get(Autor, autor_id)
    if not autor:
        raise NoEncontrado(f"Autor con id={autor_id} no encontrado")
    return autor


def actualizar_autor(db: Session, autor_id: int, datos) -> Autor:
    autor = obtener_autor(db, autor_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(autor, campo, valor)
    db.commit()
    db.refresh(autor)
    return autor


def eliminar_autor(db: Session, autor_id: int) -> None:
    autor = obtener_autor(db, autor_id)
    if autor.libros:
        raise Conflicto("No se puede eliminar un autor que tiene libros")
    db.delete(autor)
    db.commit()


# ---------- LIBROS ----------


def crear_libro(db: Session, datos) -> Libro:
    if not db.get(Autor, datos.autor_id):
        raise NoEncontrado(
            f"No existe el autor con id={datos.autor_id}. Crea el autor primero."
        )
    if db.scalar(select(Libro).where(Libro.isbn == datos.isbn)):
        raise Conflicto(f"Ya existe un libro con el ISBN {datos.isbn}")

    # Validar que todas las categorías existan (1 a 5, ya validado en el schema)
    categorias = list(db.scalars(select(Categoria).where(Categoria.id.in_(datos.categoria_ids))))
    if len(categorias) != len(datos.categoria_ids):
        raise NoEncontrado("Una o más categorías no existen")

    # categoria_ids no es columna del modelo: se asocia por la relación N:M
    datos_libro = datos.model_dump(exclude={"categoria_ids"})
    libro = Libro(**datos_libro)
    libro.categorias = categorias
    db.add(libro)
    db.commit()
    db.refresh(libro)
    return libro


def listar_libros(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    titulo: str | None = None,
    autor_id: int | None = None,
    categoria_id: int | None = None,
    anio_desde: int | None = None,
    anio_hasta: int | None = None,
    disponibles: bool | None = None,
    nombre_autor: str | None = None,
    nacionalidad_autor: str | None = None,
    orden: str | None = None,
) -> tuple[list[Libro], int]:
    """Listado con FILTROS COMBINABLES y ORDEN.

    - titulo: coincidencia parcial (ILIKE), insensible a mayúsculas.
    - categoria_id: filtra por la relación N:M.
    - anio_desde / anio_hasta: rango de año de publicación.
    - disponibles=true: solo libros con ejemplares libres ahora mismo.
    - nombre_autor / nacionalidad_autor: JOIN con autores (coincidencia parcial).
    - orden: 'titulo' | '-titulo' | 'anio' | '-anio' ('-' = descendente).

    selectinload precarga autor y categorías en 2 consultas (evita el
    problema N+1 al serializar la respuesta).
    """
    consulta = select(Libro).options(selectinload(Libro.autor), selectinload(Libro.categorias))
    if titulo:
        consulta = consulta.where(Libro.titulo.ilike(f"%{titulo}%"))
    if autor_id:
        consulta = consulta.where(Libro.autor_id == autor_id)
    if categoria_id:
        consulta = consulta.where(Libro.categorias.any(Categoria.id == categoria_id))
    if anio_desde is not None:
        consulta = consulta.where(Libro.anio_publicacion >= anio_desde)
    if anio_hasta is not None:
        consulta = consulta.where(Libro.anio_publicacion <= anio_hasta)
    if disponibles:
        consulta = consulta.where(
            Libro.ejemplares
            > func.coalesce(
                select(func.count(Prestamo.id))
                .where(
                    Prestamo.libro_id == Libro.id,
                    Prestamo.fecha_devolucion.is_(None),
                )
                .scalar_subquery(),
                0,
            )
        )
    # JOIN con autores: filtros por datos del autor
    if nombre_autor:
        consulta = consulta.join(Autor, Libro.autor_id == Autor.id).where(
            Autor.nombre.ilike(f"%{nombre_autor}%")
        )
    if nacionalidad_autor:
        consulta = consulta.join(Autor, Libro.autor_id == Autor.id).where(
            Autor.nacionalidad.ilike(f"%{nacionalidad_autor}%")
        )

    # ORDEN: '-' delante significa descendente
    ordenes = {
        "titulo": (Libro.titulo.asc(),),
        "-titulo": (Libro.titulo.desc(),),
        "anio": (Libro.anio_publicacion.asc(), Libro.titulo.asc()),
        "-anio": (Libro.anio_publicacion.desc(), Libro.titulo.asc()),
    }
    if orden:
        if orden not in ordenes:
            raise ReglaNegocio(
                f"Orden '{orden}' no válido. Usa: titulo, -titulo, anio o -anio"
            )
        consulta = consulta.order_by(*ordenes[orden])

    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    items = list(db.scalars(consulta.offset(skip).limit(limit)).all())
    return items, total


def prestamos_activos_de(db: Session, libro_id: int) -> int:
    """Conteo de préstamos sin devolver de un libro."""
    return db.scalar(
        select(func.count(Prestamo.id)).where(
            Prestamo.libro_id == libro_id, Prestamo.fecha_devolucion.is_(None)
        )
    )


def obtener_libro(db: Session, libro_id: int) -> Libro:
    libro = db.get(Libro, libro_id)
    if not libro:
        raise NoEncontrado(f"Libro con id={libro_id} no encontrado")
    return libro


def actualizar_libro(db: Session, libro_id: int, datos) -> Libro:
    libro = obtener_libro(db, libro_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "autor_id" in cambios and not db.get(Autor, cambios["autor_id"]):
        raise NoEncontrado(f"El autor con id={cambios['autor_id']} no existe")
    if "isbn" in cambios and cambios["isbn"] != libro.isbn:
        if db.scalar(select(Libro).where(Libro.isbn == cambios["isbn"])):
            raise Conflicto(f"Ya existe un libro con el ISBN {cambios['isbn']}")
    # REGLA: no se pueden reducir los ejemplares por debajo de los
    # préstamos activos (habría ejemplares "negativos").
    if "ejemplares" in cambios and cambios["ejemplares"] < prestamos_activos_de(db, libro_id):
        raise ReglaNegocio(
            f"No se puede reducir a {cambios['ejemplares']} ejemplares: "
            f"hay {prestamos_activos_de(db, libro_id)} préstamos activos"
        )
    if "categoria_ids" in cambios:
        ids = cambios.pop("categoria_ids")
        categorias = list(db.scalars(select(Categoria).where(Categoria.id.in_(ids))))
        if len(categorias) != len(ids):
            raise NoEncontrado("Una o más categorías no existen")
        libro.categorias = categorias
    for campo, valor in cambios.items():
        setattr(libro, campo, valor)
    db.commit()
    db.refresh(libro)
    return libro


def eliminar_libro(db: Session, libro_id: int) -> None:
    libro = obtener_libro(db, libro_id)
    activos = prestamos_activos_de(db, libro_id)
    if activos:
        raise Conflicto(
            f"No se puede eliminar: tiene {activos} préstamo(s) activo(s)"
        )
    # El historial también referencia el libro por FK: si ya se prestó
    # alguna vez, no se puede borrar (la FK de prestamos lo impide).
    total_historial = db.scalar(select(func.count(Prestamo.id)).where(Prestamo.libro_id == libro_id))
    if total_historial:
        raise Conflicto(
            f"No se puede eliminar: tiene {total_historial} préstamo(s) en su historial"
        )
    db.delete(libro)
    db.commit()


# ---------- LIBROS POR AUTOR (endpoint dedicado) ----------


def libros_de_autor(
    db: Session, autor_id: int, skip: int = 0, limit: int = 20
) -> tuple[Autor, list[Libro], int]:
    """GET /autores/{id}/libros — devuelve el autor y su lista de libros."""
    autor = obtener_autor(db, autor_id)
    consulta = select(Libro).where(Libro.autor_id == autor_id)
    total = db.scalar(
        select(func.count()).select_from(consulta.subquery())
    ) or 0
    libros = list(
        db.scalars(consulta.offset(skip).limit(limit)).all()
    )
    return autor, libros, total


def detalle_libro(db: Session, libro_id: int) -> dict:
    """Detalle con el campo calculado `disponibles`.

    Devuelve un dict porque `prestamos_activos` y `disponibles` no son
    columnas del modelo: se calculan aquí y los completa el schema.
    """
    libro = obtener_libro(db, libro_id)
    activos = prestamos_activos_de(db, libro_id)
    return {
        "id": libro.id,
        "titulo": libro.titulo,
        "isbn": libro.isbn,
        "anio_publicacion": libro.anio_publicacion,
        "ejemplares": libro.ejemplares,
        "prestamos_activos": activos,
        "disponibles": libro.ejemplares - activos,
        "autor": libro.autor,
        "categorias": libro.categorias,
    }
