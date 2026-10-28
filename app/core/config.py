"""CORE - Configuración central del proyecto.

Carga las variables del archivo .env con python-dotenv
(credenciales de la BD, SECRET_KEY, entorno, etc.).
"""
import os

from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env (raíz del proyecto)
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "biblioteca")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
