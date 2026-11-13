"""Referato y alcance de trabajos, preservando históricos sin informar."""
from alembic import op
import sqlalchemy as sa

revision = "e8c2a4f6b0d1"
down_revision = "a6c8e0f2b4d6"
branch_labels = None
depends_on = None

REUNIONES = ("trabajo_reunion_cientifica", "trabajo_reunion_cientifica_memoria_version")
REVISTAS = ("trabajos_revista", "trabajos_revista_memoria_version")


def upgrade():
    for tabla in REUNIONES + REVISTAS:
        op.add_column(tabla, sa.Column("referato", sa.Boolean(), nullable=True))
    for tabla, nombre in zip(REUNIONES, ("trabajo_reunion", "trabajo_reunion_snapshot")):
        op.add_column(tabla, sa.Column("alcance", sa.String(13), nullable=True))
        with op.batch_alter_table(tabla) as batch:
            batch.create_check_constraint(f"ck_{nombre}_alcance", "alcance IS NULL OR alcance IN ('nacional', 'internacional')")


def downgrade():
    for tabla, nombre in zip(REUNIONES, ("trabajo_reunion", "trabajo_reunion_snapshot")):
        with op.batch_alter_table(tabla) as batch:
            batch.drop_constraint(f"ck_{nombre}_alcance", type_="check")
            batch.drop_column("alcance")
    for tabla in REUNIONES + REVISTAS:
        op.drop_column(tabla, "referato")
