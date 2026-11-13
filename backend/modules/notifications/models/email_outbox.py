import datetime as dt
import uuid

from sqlalchemy import text

from extension import db


class EmailOutbox(db.Model):
    __tablename__ = "email_outbox"
    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_type = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(12), nullable=False, default="pending")
    payload_encrypted = db.Column(db.Text)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    locked_at = db.Column(db.DateTime)
    locked_by = db.Column(db.String(80))
    last_error_class = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    failed_at = db.Column(db.DateTime)
    __table_args__ = (
        db.CheckConstraint("status IN ('pending', 'processing', 'sent', 'failed', 'cancelled')", name="ck_email_outbox_status"),
        db.CheckConstraint("attempt_count >= 0", name="ck_email_outbox_attempts"),
        db.CheckConstraint("(status IN ('pending', 'processing') AND payload_encrypted IS NOT NULL) OR (status IN ('sent', 'failed', 'cancelled') AND payload_encrypted IS NULL)", name="ck_email_outbox_payload"),
        db.Index("ix_email_outbox_pending_due", "status", "next_attempt_at", postgresql_where=text("status = 'pending'"), sqlite_where=text("status = 'pending'")),
        db.Index("ix_email_outbox_lease", "status", "locked_at"),
        db.Index("ix_email_outbox_retention", "status", "updated_at"),
    )
