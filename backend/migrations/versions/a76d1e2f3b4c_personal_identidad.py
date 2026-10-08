"""Identidad documental unica para Personal, Becarios e Investigadores.

Revision ID: a76d1e2f3b4c
Revises: f4b8c6d2e9a1
"""

from alembic import op
import sqlalchemy as sa


revision = "a76d1e2f3b4c"
down_revision = "f4b8c6d2e9a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "identidad_personal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dni", sa.String(length=8), nullable=False),
        sa.Column("cuil", sa.String(length=13), nullable=False),
        sa.UniqueConstraint("dni", name="uq_identidad_personal_dni"),
        sa.UniqueConstraint("cuil", name="uq_identidad_personal_cuil"),
    )
    for tabla in ("personal", "becario", "investigador"):
        with op.batch_alter_table(tabla) as batch:
            batch.add_column(sa.Column("identidad_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(f"fk_{tabla}_identidad", "identidad_personal", ["identidad_id"], ["id"])
            batch.create_unique_constraint(f"uq_{tabla}_identidad", ["identidad_id"])


def downgrade():
    for tabla in ("investigador", "becario", "personal"):
        with op.batch_alter_table(tabla) as batch:
            batch.drop_constraint(f"uq_{tabla}_identidad", type_="unique")
            batch.drop_constraint(f"fk_{tabla}_identidad", type_="foreignkey")
            batch.drop_column("identidad_id")
    op.drop_table("identidad_personal")
