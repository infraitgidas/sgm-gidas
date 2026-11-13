"""Recuperacion por correo y unicidad normalizada de cuentas."""
from alembic import op
import sqlalchemy as sa

revision = "e5a7c9d1f3b6"
down_revision = "c3e5a7b9d1f2"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    duplicates = bind.execute(sa.text("SELECT 1 FROM usuario GROUP BY lower(trim(mail)) HAVING count(*) > 1 LIMIT 1")).first()
    if duplicates:
        raise RuntimeError("Existen correos duplicados al normalizar. Corrijalos administrativamente antes de migrar; no se fusionaron cuentas.")
    bind.execute(sa.text("UPDATE usuario SET mail = lower(trim(mail)) WHERE mail <> lower(trim(mail))"))
    op.create_index("uq_usuario_mail_normalized", "usuario", [sa.text("lower(trim(mail))")], unique=True)
    op.create_table("email_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("message_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("payload_encrypted", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("locked_at", sa.DateTime()), sa.Column("locked_by", sa.String(80)),
        sa.Column("last_error_class", sa.String(64)),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime()), sa.Column("failed_at", sa.DateTime()),
        sa.CheckConstraint("status IN ('pending', 'processing', 'sent', 'failed', 'cancelled')", name="ck_email_outbox_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_email_outbox_attempts"),
        sa.CheckConstraint("(status IN ('pending', 'processing') AND payload_encrypted IS NOT NULL) OR (status IN ('sent', 'failed', 'cancelled') AND payload_encrypted IS NULL)", name="ck_email_outbox_payload"))
    op.create_index("ix_email_outbox_pending_due", "email_outbox", ["status", "next_attempt_at"],
                    postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))
    op.create_index("ix_email_outbox_lease", "email_outbox", ["status", "locked_at"])
    op.create_index("ix_email_outbox_retention", "email_outbox", ["status", "updated_at"])
    op.create_table("password_reset_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("activated_at", sa.DateTime()), sa.Column("expires_at", sa.DateTime()),
        sa.Column("consumed_at", sa.DateTime()), sa.Column("revoked_at", sa.DateTime()),
        sa.Column("requested_ip_hmac", sa.String(64), nullable=False),
        sa.Column("requested_by_admin_id", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="SET NULL")),
        sa.Column("email_message_id", sa.Uuid(), sa.ForeignKey("email_outbox.id", ondelete="SET NULL"), unique=True),
        sa.CheckConstraint("(activated_at IS NULL AND expires_at IS NULL) OR (activated_at IS NOT NULL AND expires_at > activated_at)", name="ck_password_reset_activation"))
    for column in ("user_id", "requested_at", "expires_at", "consumed_at", "revoked_at", "requested_by_admin_id"):
        op.create_index(f"ix_password_reset_request_{column}", "password_reset_request", [column])
    op.create_index("uq_password_reset_active_user", "password_reset_request", ["user_id"], unique=True,
                    postgresql_where=sa.text("consumed_at IS NULL AND revoked_at IS NULL"),
                    sqlite_where=sa.text("consumed_at IS NULL AND revoked_at IS NULL"))


def downgrade():
    op.drop_table("password_reset_request")
    op.drop_table("email_outbox")
    op.drop_index("uq_usuario_mail_normalized", table_name="usuario")
