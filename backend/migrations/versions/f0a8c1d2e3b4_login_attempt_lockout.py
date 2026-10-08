"""Persist login attempts and lockout for submitted usernames.

Revision ID: f0a8c1d2e3b4
Revises: e77a1b2c3d4e
"""

from alembic import op
import sqlalchemy as sa


revision = "f0a8c1d2e3b4"
down_revision = "e77a1b2c3d4e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_attempt",
        sa.Column("identifier_hash", sa.String(64), primary_key=True),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("login_attempt")
