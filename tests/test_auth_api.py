from datetime import date, timedelta

from app.core.database import SessionLocal
from app.core.security import hashear_password
from app.models.autor import Autor, Libro
from app.models.prestamo import Prestamo
from app.models.usuario import RolUsuario, Usuario


def registrar(client, email="ana@example.com", nombre="Ana Torres"):
    return client.post(
        "/api/v1/auth/registro",
        json={
            "email": email,
            "nombre": nombre,
            "telefono": None,
            "password": "Biblioteca123",
            "confirmar_password": "Biblioteca123",
        },
    )


def login(client, email, password="Biblioteca123"):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    return response.json() if response.status_code == 200 else response


def crear_bibliotecario() -> Usuario:
    with SessionLocal() as db:
        usuario = Usuario(
            email="biblio@example.com",
            nombre="Bibliotecario",
            password_hash=hashear_password("Biblioteca123"),
            rol=RolUsuario.bibliotecario,
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario


def test_registro_normaliza_email_y_no_expone_hash(client):
    respuesta = registrar(client, email="ANA@EXAMPLE.COM")

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "ana@example.com"
    assert cuerpo["rol"] == "socio"
    assert cuerpo["socio_id"] is not None
    assert "password" not in cuerpo
    assert "password_hash" not in cuerpo

    duplicado = registrar(client)
    assert duplicado.status_code == 409


def test_registro_rechaza_clave_debil_y_confirmacion_distinta(client):
    datos = {
        "email": "persona@example.com",
        "nombre": "Persona Ejemplo",
        "password": "abcdefgh",
        "confirmar_password": "abcdefgh",
    }
    assert client.post("/api/v1/auth/registro", json=datos).status_code == 422

    datos["password"] = "Biblioteca123"
    datos["confirmar_password"] = "OtraClave123"
    assert client.post("/api/v1/auth/registro", json=datos).status_code == 422


def test_login_tokens_y_reutilizacion_revoca_toda_la_sesion(client):
    registrar(client)
    credencial_incorrecta = login(client, "ana@example.com", "Incorrecta123")
    usuario_inexistente = login(client, "no-existe@example.com", "Incorrecta123")
    assert credencial_incorrecta.status_code == usuario_inexistente.status_code == 401
    assert credencial_incorrecta.json() == usuario_inexistente.json()

    acceso = login(client, "ana@example.com")
    assert acceso["token_type"] == "bearer"
    assert acceso["expires_in"] == 900
    assert client.get("/api/v1/auth/me").headers["www-authenticate"] == "Bearer"

    cabecera = {"Authorization": f"Bearer {acceso['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=cabecera).status_code == 200
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {acceso['refresh_token']}"},
    ).status_code == 401
    alterado = acceso["access_token"][:-1] + ("a" if acceso["access_token"][-1] != "a" else "b")
    token_alterado = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {alterado}"},
    )
    assert token_alterado.status_code == 401
    assert token_alterado.headers["www-authenticate"] == "Bearer"

    rotado = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": acceso["refresh_token"]}
    )
    assert rotado.status_code == 200
    reutilizado = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": acceso["refresh_token"]}
    )
    assert reutilizado.status_code == 401
    revocado = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotado.json()["refresh_token"]},
    )
    assert revocado.status_code == 401


def test_login_bloquea_despues_de_cinco_intentos(client):
    registrar(client)
    for _ in range(5):
        assert login(client, "ana@example.com", "Incorrecta123").status_code == 401

    bloqueado = login(client, "ana@example.com")
    assert bloqueado.status_code == 423
    assert bloqueado.json()["detail"] == "Cuenta bloqueada temporalmente"


def test_limiter_devuelve_429_en_el_login(client):
    for intento in range(11):
        respuesta = client.post(
            "/api/v1/auth/login",
            data={"username": f"desconocido{intento}@example.com", "password": "x"},
        )
    assert respuesta.status_code == 429


def test_health_y_cambio_password_revoca_refresh(client):
    salud = client.get("/api/v1/health")
    assert salud.status_code == 200
    assert salud.json() == {"status": "ok", "database": "ok"}
    assert "X-Request-ID" in salud.headers

    registrar(client)
    tokens = login(client, "ana@example.com")
    cambio = client.patch(
        "/api/v1/auth/me/password",
        json={
            "password_actual": "Biblioteca123",
            "password_nueva": "NuevaBiblioteca456",
        },
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert cambio.status_code == 204
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 401
    assert login(client, "ana@example.com", "NuevaBiblioteca456")["token_type"] == "bearer"


def test_catalogo_publico_y_mutacion_restringida_por_rol(client):
    crear_bibliotecario()
    registrar(client)
    token_socio = login(client, "ana@example.com")["access_token"]
    token_biblio = login(client, "biblio@example.com")["access_token"]

    listado = client.get("/api/v1/autores")
    assert listado.status_code == 200
    assert listado.json() == {"items": [], "total": 0, "skip": 0, "limit": 10}

    datos = {"nombre": "Isabel Allende", "nacionalidad": "Chilena"}
    denegado = client.post(
        "/api/v1/autores",
        json=datos,
        headers={"Authorization": f"Bearer {token_socio}"},
    )
    assert denegado.status_code == 403

    creado = client.post(
        "/api/v1/autores",
        json=datos,
        headers={"Authorization": f"Bearer {token_biblio}"},
    )
    assert creado.status_code == 201
    eliminado = client.delete(
        f"/api/v1/autores/{creado.json()['id']}",
        headers={"Authorization": f"Bearer {token_biblio}"},
    )
    assert eliminado.status_code == 403


def test_socio_solo_consulta_sus_prestamos_y_perfil(client):
    primero = registrar(client, "ana@example.com", "Ana Torres").json()
    segundo = registrar(client, "luis@example.com", "Luis Perez").json()
    crear_bibliotecario()
    token_ana = login(client, "ana@example.com")["access_token"]
    token_luis = login(client, "luis@example.com")["access_token"]
    token_biblio = login(client, "biblio@example.com")["access_token"]

    with SessionLocal() as db:
        autor = Autor(nombre="Autor De Prueba")
        db.add(autor)
        db.flush()
        libro = Libro(
            titulo="Libro De Prueba",
            isbn="9780140447677",
            anio_publicacion=2020,
            ejemplares=2,
            autor_id=autor.id,
        )
        db.add(libro)
        db.flush()
        prestamo_ana = Prestamo(
            libro_id=libro.id,
            socio_id=primero["socio_id"],
            fecha_prestamo=date.today(),
            fecha_limite=date.today() + timedelta(days=14),
            multa=0,
            multa_pagada=True,
            registrado_por_id=1,
        )
        prestamo_luis = Prestamo(
            libro_id=libro.id,
            socio_id=segundo["socio_id"],
            fecha_prestamo=date.today(),
            fecha_limite=date.today() + timedelta(days=14),
            multa=0,
            multa_pagada=True,
            registrado_por_id=1,
        )
        db.add_all([prestamo_ana, prestamo_luis])
        db.commit()
        prestamo_luis_id = prestamo_luis.id

    propia = client.get(
        "/api/v1/prestamos?socio_id=999",
        headers={"Authorization": f"Bearer {token_ana}"},
    )
    assert propia.status_code == 200
    assert propia.json()["total"] == 1
    assert propia.json()["items"][0]["socio_id"] == primero["socio_id"]

    oculta = client.get(
        f"/api/v1/prestamos/{prestamo_luis_id}",
        headers={"Authorization": f"Bearer {token_ana}"},
    )
    assert oculta.status_code == 404

    perfil = client.get(
        "/api/v1/socios/me", headers={"Authorization": f"Bearer {token_ana}"}
    )
    assert perfil.status_code == 200
    perfil_prohibido = client.patch(
        "/api/v1/socios/me",
        json={"activo": False},
        headers={"Authorization": f"Bearer {token_ana}"},
    )
    assert perfil_prohibido.status_code == 422

    historial = client.get(
        "/api/v1/socios/me/prestamos",
        headers={"Authorization": f"Bearer {token_luis}"},
    )
    assert historial.json()["total"] == 1
