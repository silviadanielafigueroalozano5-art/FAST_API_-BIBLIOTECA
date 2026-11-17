"""SEMILLA - Autores, categorías, libros y portadas de ejemplo.

Crea datos base para probar la API y les asocia imágenes de portada:
- Si Cloudinary está configurado (.env), sube cada imagen y guarda su enlace
  en libros.imagen_url (recomendado, así la API devuelve el enlace de Cloudinary).
- Si no, guarda la URL pública original de la imagen como imagen_url
  (imagen accesible igualmente, pero sin pasar por Cloudinary).

Uso:  python -m app.scripts.seed
"""

import asyncio
import httpx

from app.core.cloudinary_uploader import _configurar, subir_portada
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.autor import Autor, Libro
from app.models.categoria import Categoria

# ---------- Datos de ejemplo ----------

AUTORES = [
    {
        "nombre": "Joseph Sheridan Le Fanu",
        "nacionalidad": "Irlandesa",
        "anio_nacimiento": 1814,
    },
    {"nombre": "Mary Shelley", "nacionalidad": "Británica", "anio_nacimiento": 1797},
    {"nombre": "Bram Stoker", "nacionalidad": "Irlandesa", "anio_nacimiento": 1847},
    {
        "nombre": "Gabriel Garcia Marquez",
        "nacionalidad": "Colombiana",
        "anio_nacimiento": 1927,
    },
    {"nombre": "Isabel Allende", "nacionalidad": "Chilena", "anio_nacimiento": 1942},
]

CATEGORIAS = ["Terror", "Clásico", "Realismo mágico", "Novela", "Fantasia"]

# (titulo, isbn, anio, ejemplares, autor_idx, [cat_idxs], url_portada)
LIBROS = [
    (
        "Carmilla",
        "9780140447677",
        1872,
        3,
        0,
        [0, 1],
        "https://www.gutenberg.org/cache/epub/32835/pg32835.cover.medium.jpg",
    ),
    (
        "Frankenstein",
        "9780141439471",
        1818,
        4,
        1,
        [1, 4],
        "https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg",
    ),
    (
        "Dracula",
        "9780140433814",
        1897,
        5,
        2,
        [0, 1],
        "https://www.gutenberg.org/cache/epub/345/pg345.cover.medium.jpg",
    ),
    (
        "Cien Anos De Soledad",
        "9780307474728",
        1967,
        4,
        3,
        [2, 3],
        "https://covers.openlibrary.org/b/isbn/9780307474728-L.jpg",
    ),
    (
        "La Casa De Los Espiritus",
        "9780553380331",
        1982,
        2,
        4,
        [3],
        "https://covers.openlibrary.org/b/isbn/9780553380331-L.jpg",
    ),
]

CARPETA_PORTADAS = "https://raw.githubusercontent.com/"  # solo referencia


async def subir_a_cloudinary(libro_id: int, url_origen: str) -> str | None:
    """Descarga la imagen de url_origen y la sube a Cloudinary."""
    settings = get_settings()
    if not settings.cloudinary_activa:
        return None
    _configurar()
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as cliente:
        resp = await cliente.get(url_origen)
        resp.raise_for_status()

    class _Archivo:  # adaptador mínimo tipo UploadFile
        content_type = "image/jpeg"

        async def read(self):
            return resp.content

    return await subir_portada(libro_id, _Archivo())


async def poblar() -> None:
    with SessionLocal() as db:
        if db.query(Autor).count():
            print("Ya hay autores en la BD; no se siembran datos duplicados.")
            return

        autores = [Autor(**a) for a in AUTORES]
        categorias = [Categoria(nombre=n) for n in CATEGORIAS]
        db.add_all(autores + categorias)
        db.commit()

        for i, (titulo, isbn, anio, ejemplares, a_idx, c_idxs, url) in enumerate(
            LIBROS
        ):
            libro = Libro(
                titulo=titulo,
                isbn=isbn,
                anio_publicacion=anio,
                ejemplares=ejemplares,
                autor_id=autores[a_idx].id,
            )
            libro.categorias = [categorias[c] for c in c_idxs]
            db.add(libro)
            db.commit()
            db.refresh(libro)

            try:
                enlace = await subir_a_cloudinary(libro.id, url)
                if enlace is None:
                    enlace = url  # sin Cloudinary: se usa la imagen pública original
                libro.imagen_url = enlace
                db.commit()
                print(f"  ✔ {titulo}: {enlace}")
            except Exception as exc:
                print(f"  ✖ {titulo}: no se pudo subir la imagen ({exc})")

        print(
            f"\nSemilla lista: {len(AUTORES)} autores, {len(CATEGORIAS)} categorías, {len(LIBROS)} libros."
        )


if __name__ == "__main__":
    asyncio.run(poblar())
