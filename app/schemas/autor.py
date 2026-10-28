"""Esquemas de validación (Pydantic) para autores y libros."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.categoria import CategoriaResponse


def formato_titulo(valor: str) -> str:
    """Regla: cada palabra empieza por mayúscula (formato título)."""
    return valor.title()


# ---------- AUTORES ----------


class AutorBase(BaseModel):
    nombre: str = Field(
        min_length=2, max_length=100, examples=["Joseph Sheridan Le Fanu"]
    )
    nacionalidad: str | None = Field(
        default=None, max_length=60, examples=["Irlandesa"]
    )
    anio_nacimiento: int | None = Field(
        default=None, ge=1000, le=date.today().year, examples=[1814]
    )

    @field_validator("nombre", "nacionalidad", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        """Regla personalizada: quita espacios sobrantes."""
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("nombre")
    @classmethod
    def nombre_en_formato_titulo(cls, valor: str) -> str:
        return formato_titulo(valor)


class AutorCrear(AutorBase):
    pass


class AutorResponse(AutorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AutorUpdate(BaseModel):
    """Para PATCH: solo se actualizan los campos enviados."""

    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    nacionalidad: str | None = Field(default=None, max_length=60)
    anio_nacimiento: int | None = Field(default=None, ge=1000, le=date.today().year)

    @field_validator("nombre", "nacionalidad", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("nombre")
    @classmethod
    def nombre_en_formato_titulo(cls, valor: str) -> str:
        return formato_titulo(valor)


# ---------- LIBROS ----------


class LibroBase(BaseModel):
    titulo: str = Field(min_length=1, max_length=150, examples=["Carmilla"])
    # 13 dígitos, se guarda como cadena (se valida como número)
    isbn: str = Field(
        min_length=13, max_length=13, pattern=r"^\d{13}$", examples=["9780140447677"]
    )
    anio_publicacion: int = Field(
        ge=1450, le=date.today().year, description="Año de publicación válido", examples=[1872]
    )
    ejemplares: int = Field(default=1, ge=1, le=50, examples=[3])
    # El cliente solo envía el ID del autor (la FK)
    autor_id: int = Field(gt=0, examples=[1])
    # categoria_ids va SOLO en LibroCrear: no es columna del modelo,
    # así LibroResponse puede serializar el ORM sin fallar.
    categoria_ids: list[int] = Field(min_length=1, max_length=5, examples=[[1, 2]])

    @field_validator("titulo", "isbn", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("titulo")
    @classmethod
    def titulo_en_formato_titulo(cls, valor: str) -> str:
        return formato_titulo(valor)

    @field_validator("categoria_ids")
    @classmethod
    def sin_repetidos(cls, ids: list[int]) -> list[int]:
        """Regla: no se admite la misma categoría dos veces."""
        if len(ids) != len(set(ids)):
            raise ValueError("No se puede repetir una categoría")
        return ids


class LibroCrear(LibroBase):
    pass


class LibroUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=150)
    isbn: str | None = Field(default=None, min_length=13, max_length=13, pattern=r"^\d{13}$")
    anio_publicacion: int | None = Field(default=None, ge=1450, le=date.today().year)
    ejemplares: int | None = Field(default=None, ge=1, le=50)
    autor_id: int | None = Field(default=None, gt=0)
    categoria_ids: list[int] | None = Field(default=None, min_length=1, max_length=5)

    @field_validator("titulo", "isbn", mode="before")
    @classmethod
    def limpiar_texto(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("titulo")
    @classmethod
    def titulo_en_formato_titulo(cls, valor: str) -> str:
        return formato_titulo(valor)

    @field_validator("categoria_ids")
    @classmethod
    def sin_repetidos(cls, ids: list[int] | None) -> list[int] | None:
        if ids and len(ids) != len(set(ids)):
            raise ValueError("No se puede repetir una categoría")
        return ids


class CategoriaIdInLibroResponse(CategoriaResponse):
    model_config = ConfigDict(from_attributes=True)


class LibroResponse(BaseModel):
    """Salida de un libro (compatible con el ORM).

    categoria_ids se recalcula desde la relación N:M con @computed_field:
    así el schema de salida no exige una columna que no existe en el modelo.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    isbn: str
    anio_publicacion: int
    ejemplares: int
    autor_id: int
    autor: AutorResponse
    categorias: list[CategoriaIdInLibroResponse] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def categoria_ids(self) -> list[int]:
        return [c.id for c in self.categorias]
# ---------- DETALLE DE LIBRO (campo calculado) ----------


class LibroDetalle(BaseModel):
    """Libro con su disponibilidad calculada.

    - `prestamos_activos`: préstamos sin devolver (sale del controller).
    - `disponibles`: ejemplares - préstamos activos.
    """

    id: int
    titulo: str
    isbn: str
    anio_publicacion: int
    ejemplares: int
    prestamos_activos: int = 0
    disponibles: int = 0
    autor: AutorResponse
    categorias: list[CategoriaIdInLibroResponse] = []

    model_config = ConfigDict(from_attributes=True)
