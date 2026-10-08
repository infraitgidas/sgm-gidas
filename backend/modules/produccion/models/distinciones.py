from extension import db
from modules.shared.models.audit_mixin import AuditMixin

class DistincionRecibida(db.Model, AuditMixin):
    __tablename__ = 'distincion_recibida'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    # --- Claves Foráneas y Relaciones ---
    proyecto_investigacion_id = db.Column(db.Integer, db.ForeignKey('proyecto_investigacion.id'))

    proyecto_investigacion = db.relationship('ProyectoInvestigacion', back_populates='distinciones')

    def serialize(self):
        data = self.to_dict()
        data.pop("proyecto_investigacion_id")
        data["proyecto"] = {
            "id": self.proyecto_investigacion.id,
            "codigo": self.proyecto_investigacion.codigo_proyecto,
            "nombre": self.proyecto_investigacion.nombre_proyecto
        } if self.proyecto_investigacion else None

        return data


class DistincionRecibidaMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "distincion_recibida_memoria_version"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    distincion_id = db.Column(
        db.Integer,
        db.ForeignKey("distincion_recibida.id"),
        nullable=False
    )

    fecha = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    proyecto_investigacion_id = db.Column(
        db.Integer,
        db.ForeignKey("proyecto_investigacion.id"),
        nullable=True
    )
    proyecto_codigo = db.Column(db.String(50), nullable=True)
    proyecto_nombre = db.Column(db.Text, nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    distincion = db.relationship("DistincionRecibida", lazy="joined")
    proyecto_investigacion = db.relationship("ProyectoInvestigacion", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "distincion_id",
            name="uq_distincion_memoria_version"
        ),
    )

    def serialize(self):
        return self.to_dict()
