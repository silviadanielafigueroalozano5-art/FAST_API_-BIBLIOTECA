from datetime import date, timedelta
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.security import hashear_password
from app.models.autor import Autor, Libro
from app.models.prestamo import Prestamo
from app.models.socio import Socio
from app.models.usuario import RolUsuario, Usuario
from tests.test_auth_api import login, registrar


def crear_usuario(email: str, rol: RolUsuario) -> Usuario:
    with SessionLocal() as db:
        usuario = Usuario(
            email=email,
            nombre=email.split("@")[0].title(),
            password_hash=hashear_password("Biblioteca123"),
            rol=rol,
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario


def test_admin_no_puede_quitarse_rol_y_desactivar_revoca_token(client):
    admin = crear_usuario("admin@example.com", RolUsuario.admin)
    trabajador = crear_usuario("biblio@example.com", RolUsuario.bibliotecario)
    token_admin = login(client, "admin@example.com")["access_token"]
    token_trabajador = login(client, "biblio@example.com")["access_token"]
    headers = {"Authorization": f"Bearer {token_admin}"}

    propio = client.patch(
        f"/api/v1/usuarios/{admin.id}/rol",
        json={"rol": "socio"},
        headers=headers,
    )
    assert propio.status_code == 422

    listado = client.get("/api/v1/usuarios", headers=headers)
    assert listado.status_code == 200
    assert listado.json()["total"] == 2

    desactivado = client.patch(
        f"/api/v1/usuarios/{trabajador.id}/activo",
        json={"activo": False},
        headers=headers,
    )
    assert desactivado.status_code == 200
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_trabajador}"},
    ).json()["detail"] == "Usuario inactivo"


def test_cerrar_sesion_revoca_refresh_token(client):
    registrar(client)
    tokens = login(client, "ana@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    salida = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert salida.status_code == 204
    renovacion = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert renovacion.status_code == 401


def test_pago_de_multa_y_bloqueo_de_nuevo_prestamo(client):
    socio_data = registrar(client).json()
    biblio = crear_usuario("biblio@example.com", RolUsuario.bibliotecario)
    token = login(client, "biblio@example.com")["access_token"]

    with SessionLocal() as db:
        socio = db.get(Socio, socio_data["socio_id"])
        autor = Autor(nombre="Autor De Multas")
        db.add(autor)
        db.flush()
        libro = Libro(
            titulo="Libro De Multas",
            isbn="9780140447677",
            anio_publicacion=2020,
            ejemplares=2,
            autor_id=autor.id,
        )
        db.add(libro)
        db.flush()
        prestamo = Prestamo(
            libro_id=libro.id,
            socio_id=socio.id,
            fecha_prestamo=date.today() - timedelta(days=20),
            fecha_limite=date.today() - timedelta(days=13),
            fecha_devolucion=date.today(),
            multa=Decimal("6.50"),
            multa_pagada=False,
            registrado_por_id=biblio.id,
        )
        db.add(prestamo)
        db.commit()
        prestamo_id = prestamo.id
        libro_id = libro.id
        socio_id = socio.id

    headers = {"Authorization": f"Bearer {token}"}
    bloqueado = client.post(
        "/api/v1/prestamos",
        json={"libro_id": libro_id, "socio_id": socio_id},
        headers=headers,
    )
    assert bloqueado.status_code == 422
    assert bloqueado.json()["detail"] == "El socio tiene multas pendientes"

    pagada = client.post(
        f"/api/v1/prestamos/{prestamo_id}/pago-multa", headers=headers
    )
    assert pagada.status_code == 200
    assert pagada.json()["multa_pagada"] is True

    repetida = client.post(
        f"/api/v1/prestamos/{prestamo_id}/pago-multa", headers=headers
    )
    assert repetida.status_code == 409


def test_registro_de_prestamo_devolucion_y_multa(client):
    socio = registrar(client).json()
    biblio = crear_usuario("biblio@example.com", RolUsuario.bibliotecario)
    token = login(client, "biblio@example.com")["access_token"]

    with SessionLocal() as db:
        autor = Autor(nombre="Autor De Prestamo")
        db.add(autor)
        db.flush()
        libro = Libro(
            titulo="Libro De Prestamo",
            isbn="9780140447677",
            anio_publicacion=2020,
            ejemplares=1,
            autor_id=autor.id,
        )
        db.add(libro)
        db.commit()
        libro_id = libro.id

    headers = {"Authorization": f"Bearer {token}"}
    fecha_prestamo = date.today() - timedelta(days=20)
    creado = client.post(
        "/api/v1/prestamos",
        json={
            "libro_id": libro_id,
            "socio_id": socio["socio_id"],
            "fecha_prestamo": fecha_prestamo.isoformat(),
            "dias": 7,
        },
        headers=headers,
    )
    assert creado.status_code == 201
    with SessionLocal() as db:
        prestamo = db.get(Prestamo, creado.json()["id"])
        assert prestamo.registrado_por_id == biblio.id

    repetido = client.post(
        "/api/v1/prestamos",
        json={"libro_id": libro_id, "socio_id": socio["socio_id"]},
        headers=headers,
    )
    assert repetido.status_code == 422
    assert repetido.json()["detail"] == "El socio tiene préstamos vencidos"

    devuelto = client.post(
        f"/api/v1/prestamos/{creado.json()['id']}/devolucion",
        json={"fecha_devolucion": date.today().isoformat()},
        headers=headers,
    )
    assert devuelto.status_code == 200
    assert devuelto.json()["multa"] == "6.50"
    assert devuelto.json()["dias_retraso"] == 13


def test_socio_puede_solicitar_prestamo_propio(client):
    socio = registrar(client).json()
    token = login(client, "ana@example.com")["access_token"]

    with SessionLocal() as db:
        autor = Autor(nombre="Autora Solicitud")
        db.add(autor)
        db.flush()
        libro = Libro(
            titulo="Libro Solicitado",
            isbn="9780140447677",
            anio_publicacion=2020,
            ejemplares=1,
            autor_id=autor.id,
        )
        db.add(libro)
        db.commit()
        libro_id = libro.id

    headers = {"Authorization": f"Bearer {token}"}
    respuesta = client.post(
        "/api/v1/prestamos/mios",
        json={"libro_id": libro_id},
        headers=headers,
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["socio_id"] == socio["socio_id"]

    repetida = client.post(
        "/api/v1/prestamos/mios",
        json={"libro_id": libro_id},
        headers=headers,
    )
    assert repetida.status_code == 409
