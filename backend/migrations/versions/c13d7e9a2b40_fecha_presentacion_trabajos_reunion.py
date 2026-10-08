"""ISS-13: fecha de presentación en trabajos y snapshots, conservando valores."""
from alembic import op
import sqlalchemy as sa

revision = "c13d7e9a2b40"
down_revision = "b12c8d5e7f90"
branch_labels = None
depends_on = None

TABLAS = ("trabajo_reunion_cientifica", "trabajo_reunion_cientifica_memoria_version")


def _renombrar(anterior, nuevo):
    for tabla in TABLAS:
        op.alter_column(tabla, anterior, new_column_name=nuevo,
                        existing_type=sa.Date(), existing_nullable=False)


def upgrade():
    _renombrar("fecha_inicio", "fecha_presentacion")


def downgrade():
    _renombrar("fecha_presentacion", "fecha_inicio")
