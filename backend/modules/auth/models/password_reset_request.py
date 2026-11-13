import datetime as dt
import uuid

from sqlalchemy import text

from extension import db


class PasswordResetRequest(db.Model):
    __tablename__ = "password_reset_request"
    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow, index=True)
    activated_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime, index=True)
    consumed_at = db.Column(db.DateTime, index=True)
    revoked_at = db.Column(db.DateTime, index=True)
    requested_ip_hmac = db.Column(db.String(64), nullable=False)
    requested_by_admin_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="SET NULL"), index=True)
    email_message_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey("email_outbox.id", ondelete="SET NULL"), unique=True)
    __table_args__ = (
        db.Index("uq_password_reset_active_user", "user_id", unique=True,
                 postgresql_where=text("consumed_at IS NULL AND revoked_at IS NULL"),
                 sqlite_where=text("consumed_at IS NULL AND revoked_at IS NULL")),
        db.CheckConstraint("(activated_at IS NULL AND expires_at IS NULL) OR (activated_at IS NOT NULL AND expires_at > activated_at)",
                           name="ck_password_reset_activation"),
    )
