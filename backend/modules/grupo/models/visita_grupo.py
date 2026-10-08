from extension import db
from modules.shared.models.audit_mixin import AuditMixin


class TipoVisita(db.Model, AuditMixin):
    __tablename__ = "tipo_visita"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)

    visitas = db.relationship(
        "VisitaAcademica",
        back_populates="tipo_visita",
        lazy="select",
    )

    def serialize(self):
        return self.to_dict()


class VisitaAcademica(db.Model, AuditMixin):
    __tablename__ = 'visita_grupo'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    razon = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    
    # Procedencia ahora es un string en lugar de ForeignKey
    procedencia = db.Column(db.Text, nullable=False)
    
    tipo_visita_id = db.Column(
        db.Integer,
        db.ForeignKey("tipo_visita.id"),
        nullable=False,
    )
    tipo_visita = db.relationship("TipoVisita", back_populates="visitas")
    
    # --- Clave Foránea y Relación ---
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey('grupo_utn.id'))
    grupo_utn = db.relationship('GrupoInvestigacionUtn', back_populates='visitas')

    def serialize(self):
        data = self.to_dict()
        data["grupo"] = self.grupo_utn.nombre_sigla_grupo if self.grupo_utn else None
        # Procedencia ahora es un string simple
        data["procedencia"] = self.procedencia
        data["tipo_visita"] = {
            "id": self.tipo_visita.id,
            "nombre": self.tipo_visita.nombre
        }
        return data


class VisitaAcademicaMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "visita_academica_memoria_version"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    visita_academica_id = db.Column(
        db.Integer,
        db.ForeignKey("visita_grupo.id"),
        nullable=False
    )

    razon = db.Column(db.Text, nullable=False)
    procedencia = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    tipo_visita_id = db.Column(
        db.Integer,
        db.ForeignKey("tipo_visita.id"),
        nullable=False
    )
    tipo_visita_nombre = db.Column(db.String(255), nullable=True)

    grupo_utn_id = db.Column(
        db.Integer,
        db.ForeignKey("grupo_utn.id"),
        nullable=False
    )
    grupo_utn_nombre = db.Column(db.String(255), nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    visita_academica = db.relationship("VisitaAcademica", lazy="joined")
    tipo_visita = db.relationship("TipoVisita", lazy="joined")
    grupo_utn = db.relationship("GrupoInvestigacionUtn", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "visita_academica_id",
            name="uq_visita_academica_memoria_version"
        ),
    )

    def serialize(self):
        return self.to_dict()
