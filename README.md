# 📚 Taller API FastAPI — Biblioteca

API REST para gestionar los préstamos de una biblioteca: autores, categorías, libros, socios y préstamos (con multas y reportes). Construida con **Python + FastAPI + SQLAlchemy + PostgreSQL**, organizada con el **patrón MVC**.

---

## 🛠️ Instalación

1. Clona el repositorio y entra a la carpeta del proyecto.

2. Crea el entorno virtual:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate      # Windows
   source .venv/bin/activate     # Linux/Mac
   ```

3. Instala las dependencias:

   ```powershell
   pip install -r requirements.txt
   ```

4. Copia `.env.example` como `.env` y coloca tus credenciales de PostgreSQL:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Crea la base de datos **vacía** en PostgreSQL (el nombre que pusiste en `DB_NAME`). Las tablas se generan solas al arrancar la API (`Base.metadata.create_all`).

## 🚀 Ejecutar

Desde la carpeta del proyecto:

```powershell
uvicorn app.main:app --reload
```

- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs
- La API responde en formato JSON.

## 🔐 Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DB_HOST` | Host de PostgreSQL | `localhost` |
| `DB_PORT` | Puerto | `5432` |
| `DB_USER` | Usuario | `postgres` |
| `DB_PASSWORD` | Contraseña | `****` |
| `DB_NAME` | Nombre de la base de datos | `biblioteca` |

## 📁 Estructura (MVC)

```
biblioteca-api/
├── app/
│   ├── main.py           ← crea la app, registra routers y errores
│   ├── core/             ← database, config, exceptions, paginación
│   ├── models/           ← autor (+ libro), categoria (+ N:M), socio, prestamo
│   ├── schemas/          ← validación Pydantic (uno por recurso + reportes)
│   ├── controllers/      ← consultas SQL y reglas de negocio
│   └── routes/           ← endpoints HTTP (no escriben SQL)
├── scripts/              ← pruebas de los casos del taller
├── .env / .env.example / .gitignore
├── requirements.txt
└── README.md
```

## 🔗 Tabla de endpoints

### Autores
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/autores` | Lista paginada. Filtro `?nacionalidad=` |
| GET | `/autores/{id}` | Consulta un autor (404 si no existe) |
| GET | `/autores/{id}/libros` | Libros del autor |
| POST | `/autores` | Crea (409 si el nombre ya existe) |
| PATCH | `/autores/{id}` | Actualiza solo campos enviados |
| DELETE | `/autores/{id}` | Elimina (409 si tiene libros) |

### Categorías
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/categorias` | Lista paginada |
| GET | `/categorias/{id}` | Consulta una |
| POST | `/categorias` | Crea (409 si ya existe) |
| PATCH | `/categorias/{id}` | Actualiza |
| DELETE | `/categorias/{id}` | Elimina; se quita de los libros que la tenían |

### Libros
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/libros` | Lista paginada con filtros combinables: `?buscar=` (título), `?autor=` (nombre, join), `?categoria_id=`, `?desde=`/`?hasta=` (año), `?orden=titulo\|-titulo\|anio\|-anio` |
| GET | `/libros/{id}` | Detalle con autor, categorías y `disponibles` calculado |
| POST | `/libros` | Crea (404 autor/categoría inexistente, 409 ISBN duplicado) |
| PATCH | `/libros/{id}` | Actualiza; `categoria_ids` reemplaza las categorías. 422 si ejemplares < préstamos activos |
| DELETE | `/libros/{id}` | Elimina (409 si tiene préstamos sin devolver) |

### Socios
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/socios` | Lista paginada. Filtro `?activo=true/false` |
| GET | `/socios/{id}` | Consulta un socio |
| GET | `/socios/{id}/prestamos` | Préstamos del socio. Filtro `?estado=activo\|vencido\|devuelto` |
| POST | `/socios` | Crea (409 si el email ya existe) |
| PATCH | `/socios/{id}` | Actualiza |
| DELETE | `/socios/{id}` | 409 si tiene préstamos sin devolver; si solo tiene devueltos se desactiva (borrado lógico); si no tiene, se elimina |

### Préstamos
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/prestamos` | Lista paginada. Filtros `?estado=`, `?socio_id=`, `?libro_id=` |
| GET | `/prestamos/{id}` | Detalle con libro y socio anidados y estado calculado |
| POST | `/prestamos` | Registra un préstamo (reglas R1–R8) |
| POST | `/prestamos/{id}/devolucion` | Registra la devolución y calcula la multa (R9–R10) |

### Reportes
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/reportes/libros-mas-prestados?limite=5` | Libro, autor y total de préstamos, de mayor a menor |
| GET | `/reportes/categorias` | Total de libros por categoría (incluye las de 0) |
| GET | `/reportes/prestamos-vencidos` | Préstamo, título, socio, email, fecha límite y días de retraso |
| GET | `/reportes/socios-con-multas` | Socio, total de multas y préstamos vencidos |
| GET | `/reportes/autores` | Libros, ejemplares y préstamos por autor |
| GET | `/reportes/resumen` | Totales generales de la biblioteca |

### Reglas de negocio de préstamos (R1–R10)
- **R1–R2**: el socio y el libro deben existir (404).
- **R3**: el socio debe estar activo (422).
- **R4**: sin préstamos vencidos (422).
- **R5**: máximo 3 préstamos sin devolver (422).
- **R6**: no repetir el mismo libro sin devolver (409).
- **R7**: el libro debe tener ejemplares disponibles (422).
- **R8**: `fecha_limite = fecha_prestamo + dias` (1–30, por defecto 14).
- **R9–R10**: al devolver, si hay retraso: `multa = días de retraso × 0,50`.

## ✅ Pruebas

Con la base de datos creada y el `.env` configurado:

```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe scripts\prueba_casos24.py   # los 24 casos del taller
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe scripts\prueba_fase7.py     # reglas R1-R10 y reportes
```

También puedes probar todos los endpoints desde `/docs` (Swagger).

## 📄 Formato de respuestas

- Éxito: el recurso en JSON (`201` al crear, `204` al eliminar sin cuerpo).
- Error propio: `{ "detail": "mensaje" }` (400/404/409/422 según el caso).
- Error de validación: `{ "detail": [ { "loc": [...], "msg": "..." } ] }`.

## 👥 Integrantes

- [Nombre Apellido — aprendiz SENA]
