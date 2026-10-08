"""Keep one expiring form draft per user and target."""

from alembic import op
import sqlalchemy as sa


revision = "a1d7c9e2f4b6"
down_revision = "e16a0b2c4d60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "form_draft",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("record_key", sa.String(40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "module", "record_key", name="uq_form_draft_owner_target"),
    )
    op.create_index("ix_form_draft_user_id", "form_draft", ["user_id"])
    op.create_index("ix_form_draft_expires_at", "form_draft", ["expires_at"])


def downgrade():
    op.drop_index("ix_form_draft_expires_at", table_name="form_draft")
    op.drop_index("ix_form_draft_user_id", table_name="form_draft")
    op.drop_table("form_draft")
