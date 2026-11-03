"""Rate limiter compartido entre la aplicación y las rutas."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
