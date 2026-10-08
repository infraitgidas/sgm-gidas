"""ISS-14: enlace opcional de trabajos y snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "d14e8f0a3c51"
down_revision = "c13d7e9a2b40"
branch_labels = None
depends_on = None

TABLAS = ("trabajo_reunion_cientifica", "trabajos_revista", "trabajo_reunion_cientifica_memoria_version", "trabajos_revista_memoria_version")


def upgrade():
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("enlace", sa.String(2048), nullable=True))


def downgrade():
    for tabla in reversed(TABLAS):
        op.drop_column(tabla, "enlace")
