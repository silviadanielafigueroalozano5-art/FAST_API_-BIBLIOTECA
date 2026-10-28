"""Verificación de los 24 casos de prueba del enunciado del taller.

Ejecutar con el proyecto activado (crea las tablas desde cero):
    python scripts/prueba_casos24.py
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import engine
from app.main import app

c = TestClient(app)

with engine.begin() as con:
    con.execute(
        text(
            "DROP TABLE IF EXISTS prestamos, socios, libro_categoria, libros, autores, categorias CASCADE"
        )
    )
import app.models.autor  # noqa: F401,E402
import app.models.socio  # noqa: F401,E402
import app.models.prestamo  # noqa: F401,E402

from app.core.database import Base  # noqa: E402

Base.metadata.create_all(bind=engine)

ok, fallos = 0, []


def caso(n, cond, extra=""):
    global ok
    if cond:
        ok += 1
        print(f"Caso {n}: OK {extra}")
    else:
        fallos.append(n)
        print(f"Caso {n}: FALLA {extra}")


# --- Datos de prueba ---
for datos in [
    {
        "nombre": "Gabriel García Márquez",
        "nacionalidad": "Colombiana",
        "anio_nacimiento": 1927,
    },
    {"nombre": "Isabel Allende", "nacionalidad": "Chilena", "anio_nacimiento": 1942},
    {"nombre": "George Orwell", "nacionalidad": "Británica", "anio_nacimiento": 1903},
]:
    assert c.post("/autores", json=datos).status_code == 201
for nombre in ["Novela", "Realismo Mágico", "Distopía", "Poesía"]:
    assert c.post("/categorias", json={"nombre": nombre}).status_code == 201

l1 = c.post(
    "/libros",
    json={
        "titulo": "Cien años de soledad",
        "isbn": "9780307350438",
        "anio_publicacion": 1967,
        "ejemplares": 2,
        "autor_id": 1,
        "categoria_ids": [1, 2],
    },
).json()
l2 = c.post(
    "/libros",
    json={
        "titulo": "El amor en los tiempos del cólera",
        "isbn": "9780307389732",
        "anio_publicacion": 1985,
        "ejemplares": 1,
        "autor_id": 1,
        "categoria_ids": [1],
    },
).json()
l3 = c.post(
    "/libros",
    json={
        "titulo": "La casa de los espíritus",
        "isbn": "9780520052579",
        "anio_publicacion": 1982,
        "ejemplares": 2,
        "autor_id": 2,
        "categoria_ids": [1, 2],
    },
).json()
l4 = c.post(
    "/libros",
    json={
        "titulo": "1984",
        "isbn": "9780451524935",
        "anio_publicacion": 1949,
        "ejemplares": 3,
        "autor_id": 3,
        "categoria_ids": [1, 3],
    },
).json()

for datos in [
    {"nombre": "Ana Torres", "email": "ANA@example.com"},
    {"nombre": "Luis Pérez", "email": "luis@example.com"},
    {"nombre": "Marta Ruiz", "email": "marta@example.com"},
]:
    assert c.post("/socios", json=datos).status_code == 201

hoy = date.today()

# --- 24 casos ---
r = c.post("/autores", json={"nombre": "Gabriel García Márquez"})
caso(1, r.status_code == 409, f"-> {r.status_code}")

r = c.post(
    "/libros",
    json={
        "titulo": "Prueba",
        "isbn": "123",
        "anio_publicacion": 2000,
        "ejemplares": 1,
        "autor_id": 1,
        "categoria_ids": [1],
    },
)
caso(2, r.status_code == 422, f"-> {r.status_code}")

r = c.post(
    "/libros",
    json={
        "titulo": "Prueba",
        "isbn": "1111111111111",
        "anio_publicacion": 2000,
        "ejemplares": 1,
        "autor_id": 1,
        "categoria_ids": [1, 1],
    },
)
caso(3, r.status_code == 422, f"-> {r.status_code}")

r = c.post(
    "/libros",
    json={
        "titulo": "Prueba",
        "isbn": "1111111111111",
        "anio_publicacion": 2000,
        "ejemplares": 1,
        "autor_id": 99,
        "categoria_ids": [1],
    },
)
caso(4, r.status_code == 404, f"-> {r.status_code}")

r = c.get("/libros?categoria_id=2&orden=-anio")
titulos = [b["titulo"] for b in r.json()]
anios = [b["anio_publicacion"] for b in r.json()]
caso(5, len(r.json()) == 2 and anios == sorted(anios, reverse=True), f"-> {titulos}")

r = c.get("/libros?autor=gabriel")
caso(6, len(r.json()) == 2, f"-> {len(r.json())} libros")

r = c.post("/prestamos", json={"libro_id": 2, "socio_id": 1})
caso(7, r.status_code == 201 and r.json()["estado"] == "activo", f"-> {r.status_code}")

r = c.post("/prestamos", json={"libro_id": 2, "socio_id": 2})
caso(8, r.status_code == 422, f"-> {r.status_code}")

r = c.get("/libros/2")
caso(9, r.json()["disponibles"] == 0, f"-> disponibles={r.json()['disponibles']}")

hace20 = (hoy - timedelta(days=20)).isoformat()
r = c.post(
    "/prestamos",
    json={"libro_id": 1, "socio_id": 2, "fecha_prestamo": hace20, "dias": 7},
)
p_vencido = r.json()
caso(
    10, r.status_code == 201 and p_vencido["estado"] == "vencido", f"-> {r.status_code}"
)

r = c.post("/prestamos", json={"libro_id": 4, "socio_id": 2})
caso(11, r.status_code == 422, f"-> {r.status_code}")

r = c.get("/reportes/prestamos-vencidos")
fila = next((x for x in r.json() if x["prestamo_id"] == p_vencido["id"]), None)
caso(
    12,
    fila is not None and fila["dias_retraso"] == 13,
    f"-> dias_retraso={fila['dias_retraso'] if fila else 'no está'}",
)

r = c.post(f"/prestamos/{p_vencido['id']}/devolucion")
caso(
    13,
    r.status_code == 200 and float(r.json()["multa"]) == 6.5,
    f"-> multa={r.json().get('multa')}",
)

r = c.post(f"/prestamos/{p_vencido['id']}/devolucion")
caso(14, r.status_code == 409, f"-> {r.status_code}")

for libro in [1, 3, 4]:
    c.post("/prestamos", json={"libro_id": libro, "socio_id": 3})
r = c.post("/prestamos", json={"libro_id": 2, "socio_id": 3})
caso(15, r.status_code == 422, f"-> {r.status_code}")

r = c.patch("/libros/4", json={"ejemplares": 0})
caso(16, r.status_code == 422, f"-> {r.status_code}")

r = c.delete("/autores/1")
caso(17, r.status_code == 409, f"-> {r.status_code}")

r = c.delete("/libros/2")
caso(18, r.status_code == 409, f"-> {r.status_code}")

r = c.delete("/socios/2")
caso(19, r.status_code == 204, f"-> {r.status_code}")
r = c.get("/socios/2")
caso(19, r.json()["activo"] is False, f"-> activo={r.json()['activo']}")

r = c.post("/prestamos", json={"libro_id": 4, "socio_id": 2})
caso(20, r.status_code == 422, f"-> {r.status_code}")

r = c.get("/reportes/categorias")
poesia = next((x for x in r.json() if x["categoria"] == "poesía"), None)
caso(
    21,
    poesia is not None and poesia["total_libros"] == 0,
    f"-> {poesia if poesia else 'no está'}",
)

r = c.get("/reportes/socios-con-multas")
caso(
    22,
    len(r.json()) == 1
    and r.json()[0]["nombre"] == "Luis Pérez"
    and float(r.json()[0]["multa_total"]) == 6.5,
    f"-> {[(x['nombre'], x['multa_total']) for x in r.json()]}",
)

r = c.get("/reportes/libros-mas-prestados?limite=3")
caso(23, len(r.json()) <= 3, f"-> {len(r.json())} libros")

r1 = c.get("/libros?skip=0&limit=2")
r2 = c.get("/libros?skip=2&limit=2")
ids1, ids2 = [b["id"] for b in r1.json()], [b["id"] for b in r2.json()]
caso(
    24,
    len(ids1) == 2 and len(ids2) == 2 and not set(ids1) & set(ids2),
    f"-> p1={ids1} p2={ids2}",
)

print(f"\n{ok} verificaciones OK, {len(fallos)} fallas: {fallos or 'ninguna'}")
