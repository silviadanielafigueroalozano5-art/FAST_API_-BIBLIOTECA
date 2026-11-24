"""Alinea la base PostgreSQL heredada y la actualiza con Alembic.

Uso seguro: primero ejecutar sin --apply para validar; después proporcionar
un respaldo válido con --backup y confirmar con --apply.
"""

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.database import engine

TABLAS_BASE = {"autores", "categorias", "libro_categoria", "libros", "prestamos", "socios"}
TABLAS_NUEVAS = {"alembic_version", "usuarios", "refresh_tokens"}

VALIDACIONES = {
    "autores duplicados": """
        SELECT count(*) FROM (
            SELECT nombre FROM autores GROUP BY nombre HAVING count(*) > 1
        ) duplicados
    """,
    "categorías duplicadas": """
        SELECT count(*) FROM (
            SELECT nombre FROM categorias GROUP BY nombre HAVING count(*) > 1
        ) duplicados
    """,
    "ISBN duplicados o vacíos": """
        SELECT count(*) FROM (
            SELECT isbn FROM libros GROUP BY isbn
            HAVING count(*) > 1 OR isbn IS NULL OR length(isbn) <> 13
        ) invalidos
    """,
    "emails duplicados al ignorar mayúsculas": """
        SELECT count(*) FROM (
            SELECT lower(email) FROM socios GROUP BY lower(email) HAVING count(*) > 1
        ) duplicados
    """,
    "datos que exceden el esquema actual": """
        SELECT
            (SELECT count(*) FROM autores
             WHERE length(nombre) > 100 OR length(nacionalidad) > 60)
          + (SELECT count(*) FROM categorias
             WHERE length(nombre) > 50 OR length(descripcion) > 200)
          + (SELECT count(*) FROM libros
             WHERE length(titulo) > 150 OR ejemplares IS NULL)
          + (SELECT count(*) FROM socios
             WHERE length(nombre) > 100 OR length(email) > 150
                OR length(telefono) > 15 OR activo IS NULL)
    """,
    "fechas de alta no nulas": """
        SELECT count(*) FROM socios WHERE fecha_alta IS NOT NULL
    """,
    "multas incompatibles con NUMERIC(10,2)": """
        SELECT count(*) FROM prestamos
        WHERE multa IS NULL
           OR abs(multa::numeric) >= 100000000
           OR multa::numeric <> round(multa::numeric, 2)
    """,
}


def validar_base(connection) -> None:
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Este procedimiento solo admite PostgreSQL.")

    inspector = inspect(connection)
    tablas = set(inspector.get_table_names())
    faltantes = TABLAS_BASE - tablas
    inesperadas = TABLAS_NUEVAS & tablas
    if faltantes:
        raise RuntimeError(f"Faltan tablas heredadas requeridas: {', '.join(sorted(faltantes))}.")
    if inesperadas:
        raise RuntimeError(
            "La base ya tiene migraciones parciales o aplicadas; "
            f"no se modificó: {', '.join(sorted(inesperadas))}."
        )

    columnas = {
        tabla: {columna["name"] for columna in inspector.get_columns(tabla)}
        for tabla in TABLAS_BASE
    }
    if "anio_naci" not in columnas["autores"] or "anio_nacimiento" in columnas["autores"]:
        raise RuntimeError("La columna de autores no coincide con el esquema legado esperado.")
    if "fecha_alta" not in columnas["socios"] or "multa" not in columnas["prestamos"]:
        raise RuntimeError("El esquema legado no coincide con el esperado.")
    if "imagen_url" in columnas["libros"] or "multa_pagada" in columnas["prestamos"]:
        raise RuntimeError("La base ya tiene cambios parciales; no se modificó.")

    for descripcion, consulta in VALIDACIONES.items():
        cantidad = connection.execute(text(consulta)).scalar_one()
        if cantidad:
            raise RuntimeError(
                f"Preflight detenido: {cantidad} caso(s) de «{descripcion}». "
                "No se modificó la base."
            )

    tipo_fecha = next(
        columna["type"]
        for columna in inspector.get_columns("socios")
        if columna["name"] == "fecha_alta"
    )
    if str(tipo_fecha).lower() != "date":
        raise RuntimeError(
            "socios.fecha_alta no es DATE; el esquema no coincide con el legado esperado."
        )


def alinear_esquema(connection) -> None:
    connection.execute(
        text("ALTER TABLE autores RENAME COLUMN anio_naci TO anio_nacimiento")
    )
    connection.execute(text("ALTER TABLE libros ALTER COLUMN isbn TYPE VARCHAR(13)"))
    connection.execute(text("ALTER TABLE libros ALTER COLUMN isbn SET NOT NULL"))
    connection.execute(text("ALTER TABLE libros ALTER COLUMN ejemplares SET NOT NULL"))
    connection.execute(text("ALTER TABLE socios ALTER COLUMN email TYPE VARCHAR(150)"))
    connection.execute(text("ALTER TABLE socios ALTER COLUMN telefono TYPE VARCHAR(15)"))
    connection.execute(text("ALTER TABLE socios ALTER COLUMN activo SET NOT NULL"))
    connection.execute(
        text(
            "ALTER TABLE socios ALTER COLUMN fecha_alta "
            "TYPE TIMESTAMP WITH TIME ZONE "
            "USING fecha_alta::timestamp AT TIME ZONE 'UTC'"
        )
    )
    connection.execute(
        text("ALTER TABLE socios ALTER COLUMN fecha_alta SET DEFAULT CURRENT_TIMESTAMP")
    )
    connection.execute(
        text(
            "ALTER TABLE prestamos ALTER COLUMN multa "
            "TYPE NUMERIC(10, 2) USING multa::numeric(10, 2)"
        )
    )
    connection.execute(text("ALTER TABLE prestamos ALTER COLUMN multa SET NOT NULL"))

    inspector = inspect(connection)
    for tabla, columna, restriccion in (
        ("autores", "nombre", "uq_autores_nombre"),
        ("categorias", "nombre", "uq_categorias_nombre"),
        ("libros", "isbn", "uq_libros_isbn"),
        ("socios", "email", "uq_socios_email"),
    ):
        _asegurar_unicidad(connection, inspector, tabla, columna, restriccion)


def _asegurar_unicidad(connection, inspector, tabla, columna, restriccion) -> None:
    constraints = [
        item
        for item in inspector.get_unique_constraints(tabla)
        if item["column_names"] == [columna]
    ]
    quote = connection.dialect.identifier_preparer.quote
    tabla_sql = quote(tabla)
    restriccion_sql = quote(restriccion)

    if len(constraints) > 1:
        raise RuntimeError(
            f"{tabla}.{columna} tiene restricciones únicas duplicadas; "
            "se requiere revisión manual."
        )
    if constraints:
        nombre = constraints[0]["name"]
        if nombre != restriccion:
            connection.execute(
                text(
                    f"ALTER TABLE {tabla_sql} RENAME CONSTRAINT "
                    f"{quote(nombre)} TO {restriccion_sql}"
                )
            )
        return

    indexes = [
        item
        for item in inspector.get_indexes(tabla)
        if item["unique"] and item["column_names"] == [columna]
    ]
    if len(indexes) > 1:
        raise RuntimeError(
            f"{tabla}.{columna} tiene índices únicos duplicados; "
            "se requiere revisión manual."
        )
    if indexes:
        nombre_indice_sql = quote(indexes[0]["name"])
        connection.execute(
            text(
                f"ALTER TABLE {tabla_sql} ADD CONSTRAINT {restriccion_sql} "
                f"UNIQUE USING INDEX {nombre_indice_sql}"
            )
        )
        return

    connection.execute(
        text(
            f"ALTER TABLE {tabla_sql} ADD CONSTRAINT {restriccion_sql} "
            f"UNIQUE ({quote(columna)})"
        )
    )


def sincronizar_secuencias(connection) -> None:
    for tabla in ("autores", "categorias", "libros", "prestamos", "socios"):
        secuencia = connection.execute(
            text("SELECT pg_get_serial_sequence(:tabla, 'id')"),
            {"tabla": tabla},
        ).scalar_one()
        if secuencia is None:
            continue
        max_id = connection.execute(
            text(f"SELECT coalesce(max(id), 0) FROM {tabla}")
        ).scalar_one()
        connection.execute(
            text("SELECT setval(cast(:secuencia AS regclass), :valor, :llamado)"),
            {
                "secuencia": secuencia,
                "valor": max_id or 1,
                "llamado": bool(max_id),
            },
        )


def migrar() -> None:
    raiz = Path(__file__).resolve().parents[2]
    configuracion = Config(str(raiz / "alembic.ini"))
    with engine.begin() as connection:
        validar_base(connection)
        alinear_esquema(connection)
        configuracion.attributes["connection"] = connection
        command.stamp(configuracion, "0001_estado_inicial")
        command.upgrade(configuracion, "head")
        sincronizar_secuencias(connection)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="aplica la alineación y las migraciones; sin esta opción solo valida",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        help="ruta a un respaldo PostgreSQL válido, requerido junto con --apply",
    )
    argumentos = parser.parse_args()

    if argumentos.apply:
        if argumentos.backup is None or not argumentos.backup.is_file():
            parser.error("--apply requiere --backup con un archivo existente.")
        with argumentos.backup.open("rb") as respaldo:
            if respaldo.read(5) != b"PGDMP":
                parser.error("--backup debe ser un respaldo pg_dump en formato Custom (-Fc).")
        migrar()
        print("Migración completada: base alineada y Alembic en head.")
        return

    with engine.connect() as connection:
        validar_base(connection)
    print("Preflight correcto; no se modificó la base.")
    print("Para aplicar: --apply --backup <ruta-al-respaldo-validado>")


if __name__ == "__main__":
    main()
