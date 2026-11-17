"""Asigna imágenes de portada a los libros YA EXISTENTES en la BD.

Descarga la imagen de cada URL pública y la sube a Cloudinary si hay
credenciales en el .env; si no, guarda la URL original en imagen_url.

Uso:  python -c "import sys; sys.path.insert(0,'.'); exec(open('scripts/asignar_imagenes.py').read())"
"""

import asyncio

import httpx
from sqlalchemy import select

from app.core.cloudinary_uploader import _configurar, subir_portada
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.autor import Libro

# URLs de portadas reales (Open Library / Proyecto Gutenberg)
PORTADAS = {
    "9780307350438": "https://covers.openlibrary.org/b/isbn/9780307350438-L.jpg",  # Cien años de soledad
    "9780307389732": "https://covers.openlibrary.org/b/isbn/9780307389732-L.jpg",  # El amor en los tiempos del cólera
    "9788401337208": "https://covers.openlibrary.org/b/isbn/9788401337208-L.jpg",  # La casa de los espíritus
    "9788499890955": "https://covers.openlibrary.org/b/isbn/9788499890955-L.jpg",  # 1984
}


async def asignar() -> None:
    settings = get_settings()
    usar_cloudinary = settings.cloudinary_activa
    print(
        "Cloudinary:",
        (
            "ACTIVO ✔"
            if usar_cloudinary
            else "sin credenciales (se guarda la URL original)"
        ),
    )

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as cliente:
        with SessionLocal() as db:
            for libro in db.scalars(select(Libro)).all():
                url = PORTADAS.get(libro.isbn)
                if not url:
                    print(f"  - {libro.titulo}: sin URL de portada conocida, se omite")
                    continue
                resp = await cliente.get(url)
                resp.raise_for_status()

                if usar_cloudinary:

                    class _Archivo:
                        content_type = "image/jpeg"

                        async def read(self):
                            return resp.content

                    enlace = await subir_portada(libro.id, _Archivo())
                else:
                    enlace = url

                libro.imagen_url = enlace
                db.commit()
                print(f"  ✔ {libro.titulo}: {enlace}")

            print("\nListo: portadas asignadas.")


asyncio.run(asignar())
