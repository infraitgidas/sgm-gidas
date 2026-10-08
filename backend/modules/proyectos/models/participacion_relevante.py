from extension import db
from modules.shared.models.audit_mixin import AuditMixin

class ParticipacionRelevante(db.Model, AuditMixin):
    __tablename__ = 'participacion_relevante'
    id = db.Column(db.Integer, primary_key=True)
    nombre_evento = db.Column(db.Text, nullable=False) 
    forma_participacion = db.Column(db.Text, nullable=False) 
    fecha = db.Column(db.Date, nullable=False) 

    # --- Clave Foránea y Relación ---
    investigador_id = db.Column(db.Integer, db.ForeignKey('investigador.id'))
    becario_id = db.Column(db.Integer, db.ForeignKey('becario.id'))
    investigador = db.relationship('Investigador', back_populates='participaciones_relevantes')
    becario = db.relationship('Becario', back_populates='participaciones_relevantes')

    __table_args__ = (
        db.CheckConstraint(
            "(investigador_id IS NOT NULL AND becario_id IS NULL) OR "
            "(investigador_id IS NULL AND becario_id IS NOT NULL)",
            name="ck_participacion_relevante_un_participante",
        ),
    )

    @property
    def participante(self):
        return self.investigador or self.becario

    @property
    def participante_rol(self):
        return "investigador" if self.investigador_id is not None else "becario"

    def serialize(self):
        data = self.to_dict()
        participante = self.participante
        data["participante"] = {
            "rol": self.participante_rol,
            "id": self.investigador_id or self.becario_id,
            "nombre_apellido": participante.nombre_apellido if participante else None,
            "tipo": "Investigador" if self.participante_rol == "investigador" else "Becario",
        }
        data["investigador"] = self.investigador.nombre_apellido if self.investigador else None
        return data


class ParticipacionRelevanteMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "participacion_relevante_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    participacion_relevante_id = db.Column(
        db.Integer,
        db.ForeignKey("participacion_relevante.id"),
        nullable=False
    )

    nombre_evento = db.Column(db.Text, nullable=False)
    forma_participacion = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    investigador_id = db.Column(db.Integer, db.ForeignKey("investigador.id"))
    becario_id = db.Column(db.Integer, db.ForeignKey("becario.id"))
    investigador_nombre = db.Column(db.String(255), nullable=True)
    becario_nombre = db.Column(db.String(255), nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    participacion_relevante = db.relationship("ParticipacionRelevante", lazy="joined")
    investigador = db.relationship("Investigador", lazy="joined")
    becario = db.relationship("Becario", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "participacion_relevante_id",
            name="uq_participacion_relevante_memoria_version"
        ),
        db.CheckConstraint(
            "(investigador_id IS NOT NULL AND becario_id IS NULL) OR "
            "(investigador_id IS NULL AND becario_id IS NOT NULL)",
            name="ck_participacion_relevante_memoria_un_participante",
        ),
    )

    def serialize(self):
        data = self.to_dict()
        rol = "investigador" if self.investigador_id is not None else "becario"
        data["participante"] = {
            "rol": rol,
            "id": self.investigador_id if rol == "investigador" else self.becario_id,
            "nombre_apellido": (
                self.investigador_nombre if rol == "investigador" else self.becario_nombre
            ),
            "tipo": "Investigador" if rol == "investigador" else "Becario",
        }
        return data
