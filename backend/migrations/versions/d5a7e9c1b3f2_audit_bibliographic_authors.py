"""Add audit and soft deletion fields to bibliographic authors.

Revision ID: d5a7e9c1b3f2
Revises: c3d5e7f9a1b2
"""

from alembic import op
import sqlalchemy as sa


revision = "d5a7e9c1b3f2"
down_revision = "c3d5e7f9a1b2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("autor") as batch:
        batch.add_column(sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("updated_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("deleted_by", sa.Integer(), nullable=True))
        for field in ("created_by", "updated_by", "deleted_by"):
            batch.create_foreign_key(f"fk_autor_{field}_usuario", "usuario", [field], ["id"])


def downgrade():
    with op.batch_alter_table("autor") as batch:
        for field in ("deleted_by", "updated_by", "created_by"):
            batch.drop_constraint(f"fk_autor_{field}_usuario", type_="foreignkey")
            batch.drop_column(field)
        for field in ("activo", "deleted_at", "updated_at", "created_at"):
            batch.drop_column(field)
