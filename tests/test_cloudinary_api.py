from types import SimpleNamespace

from cloudinary.exceptions import Error as CloudinaryError
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.security import hashear_password
from app.models.usuario import RolUsuario, Usuario
from tests.test_auth_api import login


JPEG_VALIDO = b"\xff\xd8\xff" + b"contenido"


def test_secreto_cloudinary_vacio_no_activa_la_integracion():
    settings = Settings(
        _env_file=None,
        secret_key="x" * 32,
        cloudinary_cloud_name="demo-cloud",
        cloudinary_api_key="test-key",
        cloudinary_api_secret="",
    )

    assert not settings.cloudinary_activa


def _autorizacion_staff(client):
    with SessionLocal() as db:
        db.add(
            Usuario(
                email="portadas@example.com",
                nombre="Bibliotecario Portadas",
                password_hash=hashear_password("Biblioteca123"),
                rol=RolUsuario.bibliotecario,
                activo=True,
            )
        )
        db.commit()
    token = login(client, "portadas@example.com")["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _crear_autor_y_categoria(client, headers):
    autor = client.post(
        "/api/v1/autores",
        json={"nombre": "Mary Shelley", "nacionalidad": "Británica"},
        headers=headers,
    )
    categoria = client.post(
        "/api/v1/categorias",
        json={"nombre": "Novela", "descripcion": "Narrativa"},
        headers=headers,
    )
    assert autor.status_code == categoria.status_code == 201
    return autor.json()["id"], categoria.json()["id"]


def _formulario_libro(autor_id, categoria_id):
    return [
        ("titulo", (None, "Frankenstein")),
        ("isbn", (None, "9780141439471")),
        ("anio_publicacion", (None, "1818")),
        ("ejemplares", (None, "3")),
        ("autor_id", (None, str(autor_id))),
        ("categoria_ids", (None, str(categoria_id))),
    ]


def _configurar_cloudinary(monkeypatch, upload, destroy):
    settings = SimpleNamespace(
        cloudinary_cloud_name="demo-cloud",
        cloudinary_api_key="test-key",
        cloudinary_api_secret=SecretStr("test-secret"),
        cloudinary_activa=True,
    )
    monkeypatch.setattr("app.core.cloudinary_uploader.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.core.cloudinary_uploader.cloudinary.uploader.upload", upload
    )
    monkeypatch.setattr(
        "app.core.cloudinary_uploader.cloudinary.uploader.destroy", destroy
    )


def test_crear_y_actualizar_portada_persisten_url_y_consultas(client, monkeypatch):
    headers = _autorizacion_staff(client)
    autor_id, categoria_id = _crear_autor_y_categoria(client, headers)
    urls = iter(
        [
            "https://res.cloudinary.com/demo-cloud/image/upload/v123/biblioteca/portadas/primera.jpg",
            "https://res.cloudinary.com/demo-cloud/image/upload/v124/biblioteca/portadas/segunda.jpg",
        ]
    )
    eliminadas = []

    def subir(contenido, **kwargs):
        assert contenido == JPEG_VALIDO
        assert kwargs["folder"] == "biblioteca/portadas"
        return {"secure_url": next(urls)}

    def eliminar(public_id, **kwargs):
        eliminadas.append(public_id)
        return {"result": "ok"}

    _configurar_cloudinary(monkeypatch, subir, eliminar)
    crear = client.post(
        "/api/v1/libros/con-imagen",
        files=_formulario_libro(autor_id, categoria_id)
        + [("imagen", ("portada.jpg", JPEG_VALIDO, "image/jpeg"))],
        headers=headers,
    )

    assert crear.status_code == 201
    libro_id = crear.json()["id"]
    assert crear.json()["imagen_url"].endswith("/primera.jpg")
    listado = client.get("/api/v1/libros")
    assert listado.json()["items"][0]["imagen_url"] == crear.json()["imagen_url"]
    assert client.get(f"/api/v1/libros/{libro_id}").json()["imagen_url"] == crear.json()[
        "imagen_url"
    ]

    reemplazo = client.post(
        f"/api/v1/libros/{libro_id}/imagen",
        files={"imagen": ("portada-nueva.jpg", JPEG_VALIDO, "image/jpeg")},
        headers=headers,
    )
    assert reemplazo.status_code == 200
    assert reemplazo.json()["imagen_url"].endswith("/segunda.jpg")
    assert eliminadas == ["biblioteca/portadas/primera"]


def test_fallo_de_cloudinary_no_deja_libro_en_base(client, monkeypatch):
    headers = _autorizacion_staff(client)
    autor_id, categoria_id = _crear_autor_y_categoria(client, headers)

    def fallar_subida(*args, **kwargs):
        raise CloudinaryError("fallo simulado")

    _configurar_cloudinary(monkeypatch, fallar_subida, lambda *args, **kwargs: {})
    respuesta = client.post(
        "/api/v1/libros/con-imagen",
        files=_formulario_libro(autor_id, categoria_id)
        + [("imagen", ("portada.jpg", JPEG_VALIDO, "image/jpeg"))],
        headers=headers,
    )

    assert respuesta.status_code == 502
    assert client.get("/api/v1/libros").json()["total"] == 0


def test_archivo_que_no_es_imagen_no_se_sube_ni_crea_libro(client, monkeypatch):
    headers = _autorizacion_staff(client)
    autor_id, categoria_id = _crear_autor_y_categoria(client, headers)
    llamadas = []

    def subir(*args, **kwargs):
        llamadas.append(True)
        return {"secure_url": "https://res.cloudinary.com/demo-cloud/invalid.jpg"}

    _configurar_cloudinary(monkeypatch, subir, lambda *args, **kwargs: {})
    respuesta = client.post(
        "/api/v1/libros/con-imagen",
        files=_formulario_libro(autor_id, categoria_id)
        + [("imagen", ("portada.jpg", b"no es una imagen", "image/jpeg"))],
        headers=headers,
    )

    assert respuesta.status_code == 422
    assert llamadas == []
    assert client.get("/api/v1/libros").json()["total"] == 0


def test_fallo_de_commit_conserva_portada_anterior_y_limpia_nueva(
    client, monkeypatch
):
    headers = _autorizacion_staff(client)
    autor_id, categoria_id = _crear_autor_y_categoria(client, headers)
    urls = iter(
        [
            "https://res.cloudinary.com/demo-cloud/image/upload/v123/biblioteca/portadas/actual.jpg",
            "https://res.cloudinary.com/demo-cloud/image/upload/v124/biblioteca/portadas/temporal.jpg",
        ]
    )
    eliminadas = []

    def subir(*args, **kwargs):
        return {"secure_url": next(urls)}

    def eliminar(public_id, **kwargs):
        eliminadas.append(public_id)
        return {"result": "ok"}

    _configurar_cloudinary(monkeypatch, subir, eliminar)
    crear = client.post(
        "/api/v1/libros/con-imagen",
        files=_formulario_libro(autor_id, categoria_id)
        + [("imagen", ("portada.jpg", JPEG_VALIDO, "image/jpeg"))],
        headers=headers,
    )
    assert crear.status_code == 201
    libro_id = crear.json()["id"]

    monkeypatch.setattr(
        Session, "commit", lambda self: (_ for _ in ()).throw(RuntimeError("fallo DB"))
    )
    with TestClient(
        client.app, raise_server_exceptions=False
    ) as cliente_sin_excepciones:
        reemplazo = cliente_sin_excepciones.post(
            f"/api/v1/libros/{libro_id}/imagen",
            files={"imagen": ("portada-nueva.jpg", JPEG_VALIDO, "image/jpeg")},
            headers=headers,
        )

    assert reemplazo.status_code == 500
    assert client.get(f"/api/v1/libros/{libro_id}").json()["imagen_url"].endswith(
        "/actual.jpg"
    )
    assert eliminadas == ["biblioteca/portadas/temporal"]
