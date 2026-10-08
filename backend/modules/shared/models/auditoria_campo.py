from datetime import datetime

from extension import db
from modules.shared.services.date_time import serialize_temporal


class AuditoriaCampo(db.Model):
    __tablename__ = "auditoria_campo"

    id = db.Column(db.Integer, primary_key=True)
    entidad = db.Column(db.String(100), nullable=False)
    registro_id = db.Column(db.Integer, nullable=False)
    campo = db.Column(db.String(100), nullable=False)
    valor_anterior = db.Column(db.JSON, nullable=True)
    valor_nuevo = db.Column(db.JSON, nullable=True)
    fecha_cambio = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    memoria_id = db.Column(db.Integer, db.ForeignKey("memoria.id"), nullable=True)
    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=True
    )

    usuario = db.relationship("Usuario", lazy="joined")
    memoria = db.relationship("Memoria", lazy="joined")
    memoria_version = db.relationship("MemoriaVersion", lazy="joined")

    __table_args__ = (
        db.Index("ix_auditoria_campo_entidad_registro", "entidad", "registro_id"),
        db.Index("ix_auditoria_campo_memoria_version_id", "memoria_version_id"),
    )

    def serialize(self):
        data = {}

        for column in self.__table__.columns:
            value = getattr(self, column.name)

            value = serialize_temporal(value)

            data[column.name] = value

        data["usuario_nombre"] = (
            self.usuario.nombre_usuario if self.usuario else None
        )

        return data
