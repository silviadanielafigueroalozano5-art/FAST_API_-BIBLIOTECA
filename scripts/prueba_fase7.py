"""FASE 7 - Pruebas de integración.

Carga los datos de prueba EN ESTE ORDEN (autores -> categorías ->
libros -> socios) y verifica cada caso:
1. Carga de datos con limpieza de espacios y formato título.
2. Validaciones de duplicados (autor, ISBN, email) -> 409.
3. Reglas R1-R10 de préstamos con los códigos exactos.
4. Devolución con multa (R9/R10) y estado calculado.
5. Filtros combinables de libros y préstamos.
6. Reportes con agregados.
"""

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
from app.core.database import Base  # noqa: E402
import app.models.autor  # noqa: F401,E402
import app.models.socio  # noqa: F401,E402
import app.models.prestamo  # noqa: F401,E402

Base.metadata.create_all(bind=engine)
print("0. Tablas recreadas")

# ---------- 1. CARGA DE DATOS (en este orden) ----------

# AUTORES
autores = []
for datos in [
    {
        "nombre": "gabriel garcia marquez",
        "nacionalidad": "Colombiana",
        "anio_nacimiento": 1927,
    },
    {"nombre": "isabel allende", "nacionalidad": "Chilena", "anio_nacimiento": 1942},
    {"nombre": "george orwell", "nacionalidad": "Británica", "anio_nacimiento": 1903},
]:
    r = c.post("/autores", json=datos)
    assert r.status_code == 201, r.json()
    autores.append(r.json())
a1, a2, a3 = autores
print(f"1a. Autores: {a1['nombre']} | {a2['nombre']} | {a3['nombre']}")
assert a1["nombre"] == "Gabriel Garcia Marquez"  # formato título

# CATEGORÍAS
categorias = []
for nombre in ["Novela", "Realismo Magico", "Distopia", "Poesia"]:
    r = c.post("/categorias", json={"nombre": nombre})
    assert r.status_code == 201, r.json()
    categorias.append(r.json())
cat1, cat2, cat3, cat4 = categorias
print(f"1b. Categorías: {[x['nombre'] for x in categorias]}")

# LIBROS
l1 = c.post(
    "/libros",
    json={
        "titulo": "cien anos de soledad",
        "isbn": "9780307350438",
        "anio_publicacion": 1967,
        "ejemplares": 2,
        "autor_id": a1["id"],
        "categoria_ids": [cat1["id"], cat2["id"]],
    },
).json()
l2 = c.post(
    "/libros",
    json={
        "titulo": "el amor en los tiempos del colera",
        "isbn": "9780307389732",
        "anio_publicacion": 1985,
        "ejemplares": 1,
        "autor_id": a1["id"],
        "categoria_ids": [cat1["id"]],
    },
).json()
l3 = c.post(
    "/libros",
    json={
        "titulo": "la casa de los espiritus",
        "isbn": "9788401337208",
        "anio_publicacion": 1982,
        "ejemplares": 2,
        "autor_id": a2["id"],
        "categoria_ids": [cat1["id"], cat2["id"]],
    },
).json()
l4 = c.post(
    "/libros",
    json={
        "titulo": "1984",
        "isbn": "9788499890955",
        "anio_publicacion": 1949,
        "ejemplares": 3,
        "autor_id": a3["id"],
        "categoria_ids": [cat1["id"], cat3["id"]],
    },
).json()
print(
    f"1c. Libros: {l1['titulo']} ({l1['ejemplares']} ej.) | {l2['titulo']} ({l2['ejemplares']} ej.) | {l3['titulo']} | {l4['titulo']}"
)
assert l1["titulo"] == "Cien Anos De Soledad" and len(l1["categorias"]) == 2
assert l2["ejemplares"] == 1 and len(l2["categorias"]) == 1
assert l4["ejemplares"] == 3 and len(l4["categorias"]) == 2

# SOCIOS (email en minúsculas aunque llegue en mayúsculas)
s1 = c.post("/socios", json={"nombre": "Ana Torres", "email": "ANA@example.com"}).json()
s2 = c.post(
    "/socios", json={"nombre": "Luis Perez", "email": "luis@example.com"}
).json()
s3 = c.post(
    "/socios", json={"nombre": "Marta Ruiz", "email": "marta@example.com"}
).json()
print(f"1d. Socios: {s1['nombre']} ({s1['email']}) | {s2['nombre']} | {s3['nombre']}")
assert s1["email"] == "ana@example.com"

# ---------- 2. DUPLICADOS -> 409 ----------

r = c.post("/autores", json={"nombre": "Gabriel Garcia Marquez"})
print("2a. autor duplicado ->", r.status_code)
assert r.status_code == 409
r = c.post(
    "/libros",
    json={
        "titulo": "Otro",
        "isbn": "9780307350438",
        "anio_publicacion": 2000,
        "ejemplares": 1,
        "autor_id": a1["id"],
        "categoria_ids": [cat1["id"]],
    },
)
print("2b. ISBN duplicado ->", r.status_code)
assert r.status_code == 409
r = c.post("/socios", json={"nombre": "Otra Ana", "email": "ana@example.com"})
print("2c. email duplicado ->", r.status_code)
assert r.status_code == 409

# ---------- 3. REGLAS R1-R8 ----------

r = c.post(
    "/prestamos",
    json={"libro_id": l1["id"], "socio_id": 999, "fecha_prestamo": "2026-10-20"},
)
print("R1. socio inexistente ->", r.status_code)
assert r.status_code == 404
r = c.post(
    "/prestamos",
    json={"libro_id": 999, "socio_id": s1["id"], "fecha_prestamo": "2026-10-20"},
)
print("R2. libro inexistente ->", r.status_code)
assert r.status_code == 404

# R3: socio inactivo. Marta: le damos un préstamo devuelto y luego
# DELETE -> borrado lógico (activo=False, conservando el historial)
p_m = c.post("/prestamos", json={"libro_id": l1["id"], "socio_id": s3["id"], "fecha_prestamo": "2026-10-01", "dias": 7}).json()
c.post(f"/prestamos/{p_m['id']}/devolucion", json={"fecha_devolucion": "2026-10-02"})
r = c.delete(f"/socios/{s3['id']}")  # borrado lógico -> 204 (fase 8)
assert r.status_code == 204
# Marta quedó desactivada en la BD
assert c.get(f"/socios/{s3['id']}").json()["activo"] is False
r = c.post(
    "/prestamos",
    json={"libro_id": l1["id"], "socio_id": s3["id"], "fecha_prestamo": "2026-10-20"},
)
print("R3. socio inactivo ->", r.status_code, r.json())
assert r.status_code == 422 and r.json()["detail"] == "El socio no está activo"

# R4: préstamo vencido bloquea (Luis con límite pasado)
p_venc = c.post(
    "/prestamos",
    json={
        "libro_id": l1["id"],
        "socio_id": s2["id"],
        "fecha_prestamo": "2026-09-01",
        "dias": 7,
    },
).json()
assert p_venc["estado"] == "vencido"
r = c.post(
    "/prestamos",
    json={"libro_id": l4["id"], "socio_id": s2["id"], "fecha_prestamo": "2026-10-01"},
)
print("R4. socio con vencido ->", r.status_code, r.json())
assert (
    r.status_code == 422 and r.json()["detail"] == "El socio tiene préstamos vencidos"
)

# R5: máximo 3 sin devolver (Ana: 1º, 2º, 3º con libros distintos)
p1 = c.post(
    "/prestamos",
    json={"libro_id": l1["id"], "socio_id": s1["id"], "fecha_prestamo": "2026-10-20"},
).json()
p2 = c.post(
    "/prestamos",
    json={"libro_id": l2["id"], "socio_id": s1["id"], "fecha_prestamo": "2026-10-21"},
).json()
p3 = c.post(
    "/prestamos",
    json={"libro_id": l3["id"], "socio_id": s1["id"], "fecha_prestamo": "2026-10-22"},
).json()
r = c.post(
    "/prestamos",
    json={"libro_id": l4["id"], "socio_id": s1["id"], "fecha_prestamo": "2026-10-23"},
)
print("R5. 4to préstamo ->", r.status_code, r.json())
assert r.status_code == 422 and r.json()["detail"] == "Máximo de 3 préstamos"

# R6: mismo libro sin devolver -> 409 (probamos con Luis tras devolver su vencido)
c.post(f"/prestamos/{p_venc['id']}/devolucion", json={"fecha_devolucion": "2026-09-05"})
r6a = c.post(
    "/prestamos",
    json={"libro_id": l1["id"], "socio_id": s2["id"], "fecha_prestamo": "2026-10-01", "dias": 30},
).json()
print("R6a. Luis pide l1 ->", r6a["id"])
# SIN devolver r6a: el segundo intento del MISMO libro debe dar 409 (R6)
r = c.post(
    "/prestamos",
    json={"libro_id": l1["id"], "socio_id": s2["id"], "fecha_prestamo": "2026-10-02"},
)
print("R6b. mismo libro otra vez ->", r.status_code, r.json())
assert r.status_code == 409 and "ya tiene este libro" in r.json()["detail"]
# Ahora sí lo devolvemos dentro del plazo (límite 31-10, devuelto 10-10)
c.post(f"/prestamos/{r6a['id']}/devolucion", json={"fecha_devolucion": "2026-10-10"})

# R7: sin ejemplares. l2 tiene 1 ejemplar y lo tiene Ana sin devolver
r = c.post(
    "/prestamos",
    json={"libro_id": l2["id"], "socio_id": s2["id"], "fecha_prestamo": "2026-10-02"},
)
print("R7. sin ejemplares ->", r.status_code, r.json())
assert r.status_code == 422 and r.json()["detail"] == "No hay ejemplares disponibles"

# R8: fecha_limite = prestamo + dias (default 14)
assert p1["fecha_limite"] == "2026-11-03"  # 20-10 + 14
p_dias = c.post(
    "/prestamos",
    json={
        "libro_id": l4["id"],
        "socio_id": s2["id"],
        "fecha_prestamo": "2026-10-02",
        "dias": 30,
    },
).json()
print("R8. límites:", p1["fecha_limite"], "| con dias=30:", p_dias["fecha_limite"])
assert p_dias["fecha_limite"] == "2026-11-01"

# ---------- 4. DEVOLUCIÓN R9/R10 ----------

r = c.post(f"/prestamos/{p2['id']}/devolucion", json={"fecha_devolucion": "2026-10-20"})
print("R9b. devolución anterior ->", r.status_code)
assert r.status_code == 422
# p2 (l2, límite 04-11) devuelto el 14-11: 10 días × 0.50 = 5.00
r = c.post(f"/prestamos/{p2['id']}/devolucion", json={"fecha_devolucion": "2026-11-14"})
print("R10. multa 10 días ->", r.json())
assert float(r.json()["multa"]) == 5.00 and r.json()["dias_retraso"] == 10
r = c.post(f"/prestamos/{p2['id']}/devolucion")
print("R9a. doble devolución ->", r.status_code)
assert r.status_code == 409

det = c.get(f"/prestamos/{p2['id']}").json()
assert det["estado"] == "devuelto" and float(det["multa"]) == 5.00

# ---------- 5. FILTROS ----------

r = c.get("/libros?autor=garcia&desde=1950&disponibles=true&orden=-anio")
print(
    "5a. libros filtrados ->", [(b["titulo"], b["anio_publicacion"]) for b in r.json()]
)
titulos = [b["titulo"] for b in r.json()]
# l2 ya fue devuelto (p2): ambos libros de García Márquez disponibles,
# ordenados por año descendente
assert titulos == ["El Amor En Los Tiempos Del Colera", "Cien Anos De Soledad"]
# tras devolver p2, l2 vuelve a estar disponible:
r = c.get("/libros?buscar=colera&disponibles=true")
assert len(r.json()) == 1

r = c.get("/libros?categoria_id=%d&orden=titulo" % cat2["id"])
print("5b. por categoria 2 ->", [b["titulo"] for b in r.json()])
assert [b["titulo"] for b in r.json()] == [
    "Cien Anos De Soledad",
    "La Casa De Los Espiritus",
]

r = c.get(f"/prestamos?estado=activo&socio_id={s1['id']}")
print("5c. prestamos activos de Ana ->", [p["id"] for p in r.json()])
ids_activos = [p["id"] for p in r.json()]
print("5c. prestamos activos de Ana ->", ids_activos)
assert set(ids_activos) == {p1["id"], p3["id"]} and len(ids_activos) == 2  # orden desc por fecha

r = c.get(f"/socios/{s1['id']}/prestamos?estado=devuelto")
assert [p["id"] for p in r.json()] == [p2["id"]]

# ---------- 6. REPORTES ----------

# Creamos un vencido REAL sin devolver (Luis pide l3 con fecha antigua):
# R6 no aplica (Luis ya tiene l4 con p_dias, pero l3 no)
p_venc2 = c.post("/prestamos", json={"libro_id": l3["id"], "socio_id": s2["id"], "fecha_prestamo": "2026-09-10", "dias": 7}).json()
assert p_venc2["estado"] == "vencido"

r = c.get("/reportes/libros-mas-prestados").json()
print("6a. mas prestados ->", [(x["titulo"], x["total_prestamos"]) for x in r])
assert r[0]["titulo"] == "Cien Anos De Soledad" and r[0]["total_prestamos"] == 4  # p_m + p1 + p_venc + R6a

r = c.get("/reportes/categorias").json()
por_cat = {x["categoria"]: x["total_libros"] for x in r}
print("6b. por categoria ->", por_cat)
assert por_cat["novela"] == 4 and por_cat["poesia"] == 0

r = c.get("/reportes/prestamos-vencidos").json()
print("6c. vencidos ->", [(x["prestamo_id"], x["socio"], x["dias_retraso"]) for x in r])
assert [x["prestamo_id"] for x in r] == [p_venc2["id"]] and r[0]["dias_retraso"] > 0

r = c.get("/reportes/socios-con-multas").json()
print("6d. con multas ->", [(x["nombre"], str(x["multa_total"])) for x in r])
# Luis: vencido sin devolver (p_venc2); Ana: multa impaga de R10 (5.00)
lu = next(x for x in r if x["nombre"] == "Luis Perez")
ana = next(x for x in r if x["nombre"] == "Ana Torres")
assert float(lu["multa_total"]) > 0 and float(ana["multa_total"]) == 5.00

r = c.get("/reportes/resumen").json()
print("6e. resumen ->", r)
assert r["total_libros"] == 4 and r["total_ejemplares"] == 8
assert r["socios_activos"] == 2  # Ana y Luis (Marta dada de baja)
assert r["socios_vencidos"] == 1 and r["total_prestados"] >= 3

# DELETE de Ana: aún tiene p3 sin devolver -> 409
r = c.delete(f"/socios/{s1['id']}")
print("7. DELETE Ana con préstamo sin devolver ->", r.status_code)
assert r.status_code == 409

print("\nFASE 7 COMPLETA - TODOS LOS CASOS VERIFICADOS")
