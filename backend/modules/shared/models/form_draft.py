from datetime import datetime

from extension import db


class FormDraft(db.Model):
    __tablename__ = "form_draft"
    __table_args__ = (
        db.UniqueConstraint("user_id", "module", "record_key", name="uq_form_draft_owner_target"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True)
    module = db.Column(db.String(64), nullable=False)
    record_key = db.Column(db.String(40), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    saved_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
