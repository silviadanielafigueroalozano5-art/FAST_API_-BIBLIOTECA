# API REST segura para una biblioteca

API construida con FastAPI, SQLAlchemy 2 y PostgreSQL. Conserva los CRUD y
reglas de préstamo del Taller 1, con JWT, roles, control de propiedad,
contraseñas Argon2 y migraciones Alembic.

## Requisitos

- Python 3.12 o superior
- Docker Desktop con Docker Compose, o PostgreSQL 16

## Instalación local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Genera una clave propia y reemplaza `SECRET_KEY` en `.env`. No compartas ni
subas ese archivo:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Con Docker Compose:

```powershell
docker compose up -d db
```

O crea manualmente una base PostgreSQL vacía y ajusta `DATABASE_URL` y
`TEST_DATABASE_URL` en `.env`. Las migraciones iniciales están pensadas para
una base vacía; respalda cualquier base previa del Taller 1 antes de migrar.
La URL debe usar el driver `psycopg`, por ejemplo
`postgresql+psycopg://usuario:clave@localhost:5432/biblioteca`.

## Migraciones y ejecución

Las tablas no se crean al iniciar la API. Aplícalas desde la raíz:

```powershell
python -m alembic upgrade head
fastapi dev app/main.py
```

La API queda disponible en `http://127.0.0.1:8000`; Swagger se encuentra en
`/docs`. En `ENVIRONMENT=prod` Swagger, ReDoc y OpenAPI quedan deshabilitados.

Migraciones incluidas:

1. `0001_estado_inicial`: tablas del catálogo, socios y préstamos.
2. `0002_multa_pagada`: columna de pago y actualización de préstamos existentes.
3. `0003_usuarios`: usuarios, roles y vínculo uno a uno con socios.
4. `0004_refresh_tokens`: almacenamiento de identificadores revocables.
5. `0005_auditoria_prestamos`: usuario que registró cada préstamo.

Comandos útiles:

```powershell
python -m alembic history
python -m alembic current
python -m alembic downgrade -1
python -m alembic upgrade head
```

Cada revisión nueva debe incluir `upgrade()` y `downgrade()`. No edites
migraciones ya aplicadas: crea una revisión posterior.

## Usuarios iniciales y autenticación

El primer administrador se crea interactivamente; la contraseña se solicita
sin mostrarla en pantalla:

```powershell
python -m app.scripts.crear_admin
```

El registro público crea un usuario con rol `socio` y su perfil vinculado.
Los usuarios `bibliotecario` y `admin` solo los crea un administrador desde
`POST /api/v1/usuarios`. Las contraseñas se almacenan con Argon2; nunca se
devuelve `password_hash`.

En Swagger, usa `POST /api/v1/auth/login` con formulario OAuth2
(`username` es el email) y autoriza las peticiones protegidas con el access
token. El access token dura 15 minutos; el refresh token dura 7 días, se rota
al renovarlo y se puede revocar al cerrar sesión.

## Roles y permisos

| Operación | Anónimo | Socio | Bibliotecario | Admin |
|---|---:|---:|---:|---:|
| Registro, login, refresh y health | Sí | Sí | Sí | Sí |
| Consultar libros, autores y categorías | Sí | Sí | Sí | Sí |
| Crear y actualizar catálogo | No | No | Sí | Sí |
| Eliminar catálogo | No | No | No | Sí |
| Perfil y préstamos propios | No | Propios | No | No |
| Consultar/crear socios | No | No | Sí | Sí |
| Consultar/actualizar socio por ID | No | No | Sí | Sí |
| Eliminar socios | No | No | No | Sí |
| Consultar préstamos | No | Propios | Todos | Todos |
| Registrar, devolver préstamos y cobrar multas | No | No | Sí | Sí |
| Reportes | No | No | Sí | Sí |
| Administrar usuarios y roles | No | No | No | Sí |

Un socio que intenta consultar un préstamo ajeno recibe 404. La API limita
los intentos de login a 10 por minuto y los registros a 5 por minuto por IP.
Tras cinco intentos fallidos consecutivos, la cuenta se bloquea por 15 minutos.

## Endpoints principales

Todas las rutas usan el prefijo `/api/v1`.

| Método | Ruta | Acceso |
|---|---|---|
| GET | `/health` | Público; valida PostgreSQL |
| POST | `/auth/registro` | Público |
| POST | `/auth/login` | Público, OAuth2 Password |
| POST | `/auth/refresh` | Público; rota refresh token |
| POST | `/auth/logout` | Autenticado |
| GET | `/auth/me` | Autenticado |
| PATCH | `/auth/me/password` | Autenticado |
| GET | `/libros`, `/autores`, `/categorias` | Público |
| POST/PATCH | `/libros`, `/autores`, `/categorias` | Bibliotecario o admin |
| DELETE | `/libros/{id}`, `/autores/{id}`, `/categorias/{id}` | Admin |
| GET/PATCH | `/socios/me` | El socio propietario |
| GET | `/socios/me/prestamos`, `/socios/me/multas` | El socio propietario |
| GET/POST | `/socios` | Bibliotecario o admin |
| GET/PATCH | `/socios/{id}` | Bibliotecario o admin |
| DELETE | `/socios/{id}` | Admin |
| GET | `/prestamos`, `/prestamos/{id}` | Socio: propios; staff: todos |
| POST | `/prestamos` | Bibliotecario o admin |
| POST | `/prestamos/{id}/devolucion` | Bibliotecario o admin |
| POST | `/prestamos/{id}/pago-multa` | Bibliotecario o admin |
| GET | `/reportes/*` | Bibliotecario o admin |
| GET/POST | `/usuarios` | Admin |
| PATCH | `/usuarios/{id}/rol`, `/usuarios/{id}/activo` | Admin |

Los listados paginados usan `skip` y `limit` y responden, por ejemplo:

```json
{"items": [], "total": 0, "skip": 0, "limit": 10}
```

Las respuestas 401 incluyen `WWW-Authenticate: Bearer`. La API también
configura CORS desde `CORS_ORIGINS`, un `X-Request-ID` por petición, logs sin
credenciales ni tokens y respuestas genéricas para errores 500.

## Pruebas

Configura `TEST_DATABASE_URL` con una base de datos exclusiva para pruebas.
Cuando no se define en el entorno de pytest, las pruebas usan SQLite en memoria.

```powershell
python -m pytest
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

## Variables de entorno

| Variable | Uso |
|---|---|
| `DATABASE_URL` | URL PostgreSQL de la API |
| `TEST_DATABASE_URL` | Base aislada para pytest |
| `SECRET_KEY` | Firma JWT; mínimo 32 caracteres |
| `ALGORITHM` | Algoritmo JWT; `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Duración del refresh token |
| `CORS_ORIGINS` | Lista JSON de orígenes permitidos |
| `ENVIRONMENT` | `dev`, `test` o `prod` |
| `TASA_MULTA_DIARIA` | Valor de la multa por día |

Consulta `.env.example`. `SECRET_KEY` debe generarse de forma privada y no
debe subirse al repositorio. En producción, define explícitamente los orígenes
CORS permitidos; no se acepta `*`.

## Integrantes

- Silvia Daniela Figueroa — aprendiz SENA
