from sqlalchemy import text

from app.core.database import engine
from tests.conftest import migrate


def test_multa_pagada_migra_datos_y_revierte():
    migrate("base")
    migrate("0001_estado_inicial")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO autores (id, nombre) VALUES (1, 'Autora De Prueba')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO libros (id, titulo, isbn, anio_publicacion, ejemplares, autor_id) "
                "VALUES (1, 'Libro De Prueba', '9780140447677', 2020, 1, 1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO socios (id, nombre, email, activo) "
                "VALUES (1, 'Ana Torres', 'ana@example.com', true)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO prestamos "
                "(id, libro_id, socio_id, fecha_prestamo, fecha_limite, multa) "
                "VALUES (1, 1, 1, '2026-01-01', '2026-01-14', 0), "
                "(2, 1, 1, '2026-01-01', '2026-01-14', 6.50)"
            )
        )

    migrate("0002_multa_pagada")
    with engine.connect() as connection:
        resultados = connection.execute(
            text("SELECT id, multa_pagada FROM prestamos ORDER BY id")
        ).all()
    assert resultados == [(1, True), (2, False)]
    migrate("base")
