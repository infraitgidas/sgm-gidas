"""Store original project end and its single justified extension.

Revision ID: e77a1b2c3d4e
Revises: a76d1e2f3b4c
"""

from alembic import op
import sqlalchemy as sa


revision = "e77a1b2c3d4e"
down_revision = "a76d1e2f3b4c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("proyecto_investigacion") as batch:
        batch.add_column(sa.Column("fecha_fin_original", sa.Date(), nullable=True))
        batch.add_column(sa.Column("fecha_fin_prorrogada", sa.Date(), nullable=True))
        batch.add_column(sa.Column("prorroga_motivo", sa.Text(), nullable=True))
        batch.add_column(sa.Column("prorroga_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("prorroga_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_proyecto_prorroga_by", "usuario", ["prorroga_by"], ["id"])
    op.execute("UPDATE proyecto_investigacion SET fecha_fin_original = fecha_fin WHERE fecha_fin IS NOT NULL")


def downgrade():
    with op.batch_alter_table("proyecto_investigacion") as batch:
        batch.drop_constraint("fk_proyecto_prorroga_by", type_="foreignkey")
        batch.drop_column("prorroga_at")
        batch.drop_column("prorroga_by")
        batch.drop_column("prorroga_motivo")
        batch.drop_column("fecha_fin_prorrogada")
        batch.drop_column("fecha_fin_original")
