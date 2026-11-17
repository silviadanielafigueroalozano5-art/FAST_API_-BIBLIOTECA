"""Agrega imagen_url (enlace de Cloudinary) a la tabla libros."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_libro_imagen"
down_revision: Union[str, None] = "0005_auditoria_prestamos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("libros", sa.Column("imagen_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("libros", "imagen_url")
