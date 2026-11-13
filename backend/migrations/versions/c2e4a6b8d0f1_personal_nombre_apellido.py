"""Separate personal names without guessing historical surnames.

Revision ID: c2e4a6b8d0f1
Revises: a7c9e2f4b6d8
"""
from alembic import op
import sqlalchemy as sa

revision = "c2e4a6b8d0f1"
down_revision = "a7c9e2f4b6d8"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("personal", "becario", "investigador"):
        op.add_column(table, sa.Column("nombre", sa.String(60), nullable=True))
        op.add_column(table, sa.Column("apellido", sa.String(60), nullable=True))


def downgrade():
    for table in ("investigador", "becario", "personal"):
        op.drop_column(table, "apellido")
        op.drop_column(table, "nombre")
