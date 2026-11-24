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
6. `0006_libro_imagen`: URL de portada de cada libro.

Si conservas la base heredada del Taller 1, no ejecutes directamente
`alembic upgrade head`: no tiene una revisión de Alembic y su esquema difiere
del actual. Haz primero un respaldo PostgreSQL y ejecuta el preflight:

```powershell
python -m app.scripts.migrar_bd_legada
```

Si el preflight termina correctamente, crea un respaldo PostgreSQL en formato
Custom (pgAdmin o `pg_dump -Fc`) y aplica la alineación y las revisiones
indicando ese archivo. El procedimiento conserva las filas y los valores
existentes; no rellena las fechas de alta históricas que están nulas:

```powershell
python -m app.scripts.migrar_bd_legada --apply --backup C:\ruta\respaldo.dump
```

Este procedimiento solo acepta el esquema legado esperado y detiene la
operación si detecta datos incompatibles o migraciones parciales.

Comandos útiles:

```powershell
python -m alembic history
python -m alembic current
python -m alembic downgrade -1
python -m alembic upgrade head
```

Cada revisión nueva debe incluir `upgrade()` y `downgrade()`. No edites
migraciones ya aplicadas: crea una revisión posterior.

## Frontend Vue

El frontend está en `frontend/` y consume la API bajo `/api/v1`. Para ejecutarlo:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Abre la dirección que indique Vite (por defecto `http://localhost:5173`).
`VITE_API_URL` apunta por defecto a `http://127.0.0.1:8000`. CORS ya permite
`http://localhost:5173` en el `.env` actual; si cambias el origen o puerto,
agrega el origen exacto a `CORS_ORIGINS` en el `.env` del backend y reinicia
FastAPI.

## Despliegue en Render

La raíz del repositorio contiene la API y Alembic; no muevas `app/`,
`alembic/` ni `requirements.txt`. El frontend ya está separado en `frontend/`.
El archivo `render.yaml` configura dos servicios independientes: la API como
servicio Python y el frontend como sitio estático con fallback para Vue Router.

1. Crea una base PostgreSQL persistente en Render (o elige una ya existente).
   No uses la base local `localhost` en producción.
2. En Render, crea un Blueprint desde este repositorio y configura las
   variables marcadas `sync: false` antes del primer despliegue:
   - `DATABASE_URL`: URL interna de PostgreSQL. Las URLs `postgres://` y
     `postgresql://` se adaptan al driver `psycopg` instalado por el proyecto.
   - `CORS_ORIGINS`: lista JSON con el origen exacto del frontend, por ejemplo
     `["https://biblioteca-frontend.onrender.com"]`; nunca uses `*`.
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` y
     `CLOUDINARY_API_SECRET`: credenciales de Cloudinary.
   Render genera `SECRET_KEY` automáticamente.
3. Configura `VITE_API_URL` en el servicio estático con el origen HTTPS del
   servicio API, por ejemplo `https://biblioteca-api.onrender.com`. No agregues
   `/api/v1`; el frontend añade ese prefijo. Vuelve a desplegar el frontend
   después de cambiar esta variable.
4. El comando de inicio de la API aplica las migraciones Alembic antes de
   iniciar FastAPI. Comprueba el servicio en `/api/v1/health`.

La base PostgreSQL de Render es independiente de la base local: el despliegue
no copia los libros, usuarios ni préstamos existentes. Si necesitas conservar
los datos locales, respáldalos y planifica su importación a la base remota antes
de usarla.

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
| Solicitar préstamos propios | No | Sí | No | No |
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
| POST | `/libros/{id}/imagen` | Bibliotecario o admin; sube la portada a Cloudinary y guarda su URL |
| DELETE | `/libros/{id}`, `/autores/{id}`, `/categorias/{id}` | Admin |
| GET/PATCH | `/socios/me` | El socio propietario |
| GET | `/socios/me/prestamos`, `/socios/me/multas` | El socio propietario |
| POST | `/prestamos/mios` | Socio autenticado; registra un préstamo propio |
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

### Portadas de libros

En `/docs`, autoriza un usuario bibliotecario o admin y usa
`POST /api/v1/libros/con-imagen`. Swagger mostrará los campos del libro como
formulario `multipart/form-data`; completa `titulo`, `isbn`,
`anio_publicacion`, `ejemplares`, `autor_id` y `categoria_ids`, y selecciona
un archivo JPEG, PNG o WebP de hasta 2 MB en `imagen`. La imagen es opcional.
Si se envía, la API la carga a Cloudinary y guarda su `secure_url` en
`libros.imagen_url` antes de confirmar el alta. El `POST /api/v1/libros`
existente sigue permitiendo crear libros sin imagen mediante JSON.

Para reemplazar una portada usa `POST /api/v1/libros/{id}/imagen` y selecciona
el archivo en `imagen`. La URL nueva se guarda antes de intentar eliminar la
portada anterior. Las consultas `GET /api/v1/libros` y
`GET /api/v1/libros/{id}` devuelven `imagen_url` (nulo si no hay portada).

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
| `CLOUDINARY_CLOUD_NAME` | Nombre de la nube de Cloudinary |
| `CLOUDINARY_API_KEY` | API Key de Cloudinary |
| `CLOUDINARY_API_SECRET` | API Secret de Cloudinary |

Consulta `.env.example`. `SECRET_KEY` debe generarse de forma privada y no
debe subirse al repositorio. En producción, define explícitamente los orígenes
CORS permitidos; no se acepta `*`.

## Integrantes

- Silvia Daniela Figueroa — aprendiz SENA
