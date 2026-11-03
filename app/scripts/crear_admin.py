"""Crea el primer administrador de forma interactiva."""

from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.controllers.auth import crear_usuario_staff
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auth import UsuarioCrear


def main() -> None:
    email = input("Email del administrador: ").strip().lower()
    nombre = input("Nombre del administrador: ").strip().title()
    password = getpass("Contraseña: ")
    confirmacion = getpass("Confirmar contraseña: ")
    if password != confirmacion:
        raise ValueError("Las contraseñas no coinciden")

    datos = UsuarioCrear(
        email=email,
        nombre=nombre,
        password=password,
        rol=RolUsuario.admin,
    )
    with SessionLocal() as db:
        existente = db.scalar(select(Usuario.id).where(Usuario.email == datos.email))
        if existente:
            print("Ya existe un usuario con ese email; no se realizaron cambios.")
            return
        usuario = crear_usuario_staff(db, datos)
        print(f"Administrador creado (id={usuario.id}, email={usuario.email}).")


if __name__ == "__main__":
    main()
