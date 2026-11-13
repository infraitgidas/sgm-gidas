"""Permite actividades de docencia en curso y sus fotos sin fecha de fin.

Revision ID: c3e5a7b9d1f2
Revises: f6b8d0e2a4c6
"""
from alembic import op
import sqlalchemy as sa

revision = "c3e5a7b9d1f2"
down_revision = "f6b8d0e2a4c6"
branch_labels = None
depends_on = None

TABLAS = ("actividad_y_catedra_posgrado", "actividad_docencia_memoria_version")


def upgrade():
    for tabla in TABLAS:
        with op.batch_alter_table(tabla) as batch:
            batch.alter_column("fecha_fin", existing_type=sa.Date(), nullable=True)


def downgrade():
    for tabla in TABLAS:
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {tabla} WHERE fecha_fin IS NULL LIMIT 1")).first():
            raise RuntimeError("No se puede exigir fecha de fin mientras existan actividades o versiones en curso.")
    for tabla in TABLAS:
        with op.batch_alter_table(tabla) as batch:
            batch.alter_column("fecha_fin", existing_type=sa.Date(), nullable=False)
