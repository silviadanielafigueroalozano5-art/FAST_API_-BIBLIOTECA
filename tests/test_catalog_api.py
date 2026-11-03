from app.core.database import SessionLocal
from app.core.security import hashear_password
from app.models.usuario import RolUsuario, Usuario
from tests.test_auth_api import login


def crear_bibliotecario():
    with SessionLocal() as db:
        db.add(
            Usuario(
                email="catalogo@example.com",
                nombre="Bibliotecario Catalogo",
                password_hash=hashear_password("Biblioteca123"),
                rol=RolUsuario.bibliotecario,
                activo=True,
            )
        )
        db.commit()


def test_catalogo_conserva_crud_y_listados_paginados(client):
    crear_bibliotecario()
    token = login(client, "catalogo@example.com")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    autor = client.post(
        "/api/v1/autores",
        json={"nombre": "gabriel garcia marquez", "nacionalidad": "Colombiana"},
        headers=headers,
    )
    assert autor.status_code == 201
    categoria = client.post(
        "/api/v1/categorias",
        json={"nombre": "realismo mágico", "descripcion": "Narrativa"},
        headers=headers,
    )
    assert categoria.status_code == 201
    libro = client.post(
        "/api/v1/libros",
        json={
            "titulo": "cien años de soledad",
            "isbn": "9780307350438",
            "anio_publicacion": 1967,
            "ejemplares": 1,
            "autor_id": autor.json()["id"],
            "categoria_ids": [categoria.json()["id"]],
        },
        headers=headers,
    )
    assert libro.status_code == 201
    assert libro.json()["titulo"] == "Cien Años De Soledad"

    libros = client.get("/api/v1/libros")
    assert libros.json()["total"] == 1
    assert libros.json()["items"][0]["id"] == libro.json()["id"]
    categorias = client.get("/api/v1/categorias")
    assert categorias.json()["total"] == 1
    por_autor = client.get(f"/api/v1/autores/{autor.json()['id']}/libros")
    assert por_autor.json()["total"] == 1
    reporte = client.get("/api/v1/reportes/autores", headers=headers)
    assert reporte.json()["total"] == 1
    top = client.get("/api/v1/reportes/libros-mas-prestados", headers=headers)
    assert top.json()["total"] == 1
    resumen = client.get("/api/v1/reportes/resumen", headers=headers)
    assert resumen.status_code == 200
    assert resumen.json()["total_libros"] == 1
    multas = client.get("/api/v1/reportes/socios-con-multas", headers=headers)
    assert multas.json()["total"] == 0

    actualizado = client.patch(
        f"/api/v1/libros/{libro.json()['id']}",
        json={"ejemplares": 2},
        headers=headers,
    )
    assert actualizado.status_code == 200
    detalle = client.get(f"/api/v1/libros/{libro.json()['id']}")
    assert detalle.json()["disponibles"] == 2
