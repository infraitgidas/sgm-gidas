"""Conserva moneda original en equipamiento, transferencias y sus versiones.

Revision ID: f6b8d0e2a4c6
Revises: e4a6c8f0b2d3
"""
from alembic import op
import sqlalchemy as sa

revision = "f6b8d0e2a4c6"
down_revision = "e4a6c8f0b2d3"
branch_labels = None
depends_on = None

TABLAS = (
    ("equipamiento_grupo", "ck_equipamiento_moneda"),
    ("equipamiento_memoria_version", "ck_equipamiento_snapshot_moneda"),
    ("transferencia_socio_productiva", "ck_transferencia_moneda"),
    ("transferencia_socio_productiva_memoria_version", "ck_transferencia_snapshot_moneda"),
)


def upgrade():
    for tabla, constraint in TABLAS:
        with op.batch_alter_table(tabla) as batch:
            batch.add_column(sa.Column("moneda", sa.String(3), nullable=False, server_default="ARS"))
            batch.create_check_constraint(constraint, "moneda IN ('ARS', 'USD')")


def downgrade():
    # No descartar la moneda de importes USD durante una reversión.
    for tabla, _ in TABLAS:
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {tabla} WHERE moneda <> 'ARS' LIMIT 1")).first():
            raise RuntimeError("No se puede quitar la moneda mientras existan importes en USD.")
    for tabla, constraint in reversed(TABLAS):
        with op.batch_alter_table(tabla) as batch:
            batch.drop_constraint(constraint, type_="check")
            batch.drop_column("moneda")
