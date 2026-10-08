"""Logros del PID y su copia histórica en memorias."""
from alembic import op
import sqlalchemy as sa

revision = "a7c9e2f4b6d8"
down_revision = "d8e1f4a6b2c9"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("proyecto_investigacion", "proyecto_investigacion_memoria_version"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("logros_obtenidos", sa.Text(), nullable=True))


def downgrade():
    for table in ("proyecto_investigacion_memoria_version", "proyecto_investigacion"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("logros_obtenidos")
