from datetime import datetime

from extension import db


class UsuarioGrupoUtn(db.Model):
    """Pertenencia auditable; el rol sigue perteneciendo al usuario."""

    __tablename__ = "usuario_grupo_utn"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey("grupo_utn.id", ondelete="RESTRICT"), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="RESTRICT"))
    deleted_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="RESTRICT"))

    usuario = db.relationship("Usuario", foreign_keys=[usuario_id], back_populates="grupos_utn")
    grupo_utn = db.relationship("GrupoInvestigacionUtn", foreign_keys=[grupo_utn_id])

    __table_args__ = (
        db.Index("ix_usuario_grupo_utn_usuario_activo", "usuario_id", "activo", "grupo_utn_id"),
        db.Index("ix_usuario_grupo_utn_grupo_activo", "grupo_utn_id", "activo", "usuario_id"),
        db.Index(
            "uq_usuario_grupo_utn_activa",
            "usuario_id",
            "grupo_utn_id",
            unique=True,
            postgresql_where=db.text("activo = true AND deleted_at IS NULL"),
            sqlite_where=db.text("activo = 1 AND deleted_at IS NULL"),
        ),
    )
