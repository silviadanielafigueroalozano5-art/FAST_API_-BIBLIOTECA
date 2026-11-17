"""Subida de imágenes de portadas a Cloudinary.

Configura el SDK con las credenciales del .env y sube el archivo recibido,
devolviendo la URL pública (secure) para guardarla en libros.imagen_url.
"""

import logging
from urllib.parse import urlsplit
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from fastapi import HTTPException, UploadFile
from requests.exceptions import RequestException
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.exceptions import ReglaNegocio

logger = logging.getLogger(__name__)

FIRMAS_IMAGEN = {
    "image/jpeg": lambda contenido: contenido.startswith(b"\xff\xd8\xff"),
    "image/png": lambda contenido: contenido.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda contenido: (
        len(contenido) >= 12
        and contenido.startswith(b"RIFF")
        and contenido[8:12] == b"WEBP"
    ),
}
TAMANO_MAXIMO = 2 * 1024 * 1024
CARPETA_PORTADAS = "biblioteca/portadas"


def _configurar() -> None:
    settings = get_settings()
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=(
            settings.cloudinary_api_secret.get_secret_value()
            if settings.cloudinary_api_secret
            else None
        ),
        secure=True,
    )


async def subir_portada(libro_id: int, archivo: UploadFile) -> str:
    """Sube la imagen del libro a Cloudinary y devuelve la URL pública."""
    settings = get_settings()
    if not settings.cloudinary_activa:
        raise ReglaNegocio(
            "Cloudinary no está configurado: define CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY y CLOUDINARY_API_SECRET en el .env"
        )
    validar_firma = FIRMAS_IMAGEN.get(archivo.content_type or "")
    if validar_firma is None:
        raise ReglaNegocio("Formato no permitido. Usa JPEG, PNG o WebP")
    contenido = await archivo.read(TAMANO_MAXIMO + 1)
    if not contenido:
        raise ReglaNegocio("El archivo de imagen está vacío")
    if len(contenido) > TAMANO_MAXIMO:
        raise ReglaNegocio("La imagen no puede pesar más de 2 MB")
    if not validar_firma(contenido):
        raise ReglaNegocio("El contenido del archivo no coincide con su formato")

    _configurar()
    try:
        resultado = await run_in_threadpool(
            cloudinary.uploader.upload,
            contenido,
            folder=CARPETA_PORTADAS,
            public_id=f"libro_{libro_id}_{uuid4().hex[:8]}",
            resource_type="image",
        )
    except (CloudinaryError, RequestException) as exc:
        logger.exception("Falló la carga de portada para el libro id=%s", libro_id)
        raise HTTPException(
            status_code=502, detail="Cloudinary no pudo almacenar la imagen"
        ) from exc

    secure_url = resultado.get("secure_url")
    parsed_url = urlsplit(secure_url) if isinstance(secure_url, str) else None
    if (
        parsed_url is None
        or parsed_url.scheme != "https"
        or parsed_url.netloc != "res.cloudinary.com"
    ):
        logger.error(
            "Cloudinary devolvió una URL segura inválida para libro id=%s",
            libro_id,
        )
        raise HTTPException(
            status_code=502, detail="Cloudinary devolvió una URL de imagen inválida"
        )
    return secure_url


async def eliminar_portada(imagen_url: str) -> None:
    """Elimina una portada propia de Cloudinary; ignora enlaces externos."""
    if not imagen_url:
        return

    settings = get_settings()
    parsed_url = urlsplit(imagen_url)
    partes = [parte for parte in parsed_url.path.split("/") if parte]
    if (
        parsed_url.netloc != "res.cloudinary.com"
        or len(partes) < 6
        or partes[0] != settings.cloudinary_cloud_name
        or partes[1:3] != ["image", "upload"]
    ):
        return

    partes_public_id = partes[3:]
    if (
        partes_public_id
        and partes_public_id[0].startswith("v")
        and partes_public_id[0][1:].isdigit()
    ):
        partes_public_id = partes_public_id[1:]
    if partes_public_id[:2] != ["biblioteca", "portadas"]:
        return
    nombre = partes_public_id[-1].rsplit(".", 1)[0]
    if not nombre:
        return
    public_id = "/".join([*partes_public_id[:-1], nombre])

    _configurar()
    try:
        resultado = await run_in_threadpool(
            cloudinary.uploader.destroy, public_id, resource_type="image"
        )
    except (CloudinaryError, RequestException) as exc:
        logger.exception("Falló la eliminación de portada en Cloudinary")
        raise HTTPException(
            status_code=502, detail="No fue posible eliminar la portada anterior"
        ) from exc
    if resultado.get("result") not in {"ok", "not found"}:
        raise HTTPException(
            status_code=502, detail="Cloudinary no confirmó la eliminación de la portada"
        )
