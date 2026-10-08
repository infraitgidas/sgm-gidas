from datetime import datetime

from extension import db


class LoginAttempt(db.Model):
    """Persistent retry state keyed by an HMAC of the submitted username."""

    __tablename__ = "login_attempt"

    identifier_hash = db.Column(db.String(64), primary_key=True)
    failed_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_failed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
