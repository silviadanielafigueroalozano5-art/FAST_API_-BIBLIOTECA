"""Hash Argon2 y creación/verificación de tokens JWT."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.models.usuario import Usuario

password_hash = PasswordHash.recommended()


def hashear_password(password: str) -> str:
    return password_hash.hash(password)


def verificar_password(password: str, hash_guardado: str) -> bool:
    return password_hash.verify(password, hash_guardado)


def crear_token(
    usuario: Usuario, tipo: str, duracion: timedelta
) -> tuple[str, str, datetime]:
    ahora = datetime.now(timezone.utc)
    expira = ahora + duracion
    jti = str(uuid4())
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol.value,
        "type": tipo,
        "iat": ahora,
        "exp": expira,
        "jti": jti,
    }
    token = jwt.encode(
        payload,
        get_settings().secret_key.get_secret_value(),
        algorithm=get_settings().algorithm,
    )
    return token, jti, expira


def decodificar_token(token: str) -> dict:
    return jwt.decode(
        token,
        get_settings().secret_key.get_secret_value(),
        algorithms=[get_settings().algorithm],
    )
