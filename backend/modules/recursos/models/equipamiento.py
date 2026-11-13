from extension import db
from modules.shared.models.audit_mixin import AuditMixin

class Equipamiento(db.Model, AuditMixin):
    __tablename__ = 'equipamiento_grupo'

    id = db.Column(db.Integer, primary_key=True)
    denominacion = db.Column(db.Text, nullable=False)
    descripcion_breve = db.Column(db.Text, nullable=False)
    fecha_incorporacion = db.Column(db.Date, nullable=False)  # mejor como Date
    monto_invertido = db.Column(db.Float, nullable=False)
    moneda = db.Column(db.String(3), nullable=False, default="ARS", server_default="ARS")
    __table_args__ = (db.CheckConstraint("moneda IN ('ARS', 'USD')", name="ck_equipamiento_moneda"),)

    # --- Claves Foráneas y Relaciones ---
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey('grupo_utn.id'), nullable=False)
    grupo_utn = db.relationship('GrupoInvestigacionUtn', back_populates='equipamiento')


    def serialize(self):
        
        data = self.to_dict()
        data["grupo"] = self.grupo_utn.nombre_sigla_grupo if self.grupo_utn else None
        return data


class EquipamientoMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "equipamiento_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    equipamiento_id = db.Column(
        db.Integer,
        db.ForeignKey("equipamiento_grupo.id"),
        nullable=False
    )

    denominacion = db.Column(db.Text, nullable=False)
    descripcion_breve = db.Column(db.Text, nullable=False)
    fecha_incorporacion = db.Column(db.Date, nullable=False)
    monto_invertido = db.Column(db.Float, nullable=False)
    moneda = db.Column(db.String(3), nullable=False, default="ARS", server_default="ARS")

    grupo_utn_id = db.Column(
        db.Integer,
        db.ForeignKey("grupo_utn.id"),
        nullable=False
    )
    grupo_utn_nombre = db.Column(db.String(255), nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    equipamiento = db.relationship("Equipamiento", lazy="joined")
    grupo_utn = db.relationship("GrupoInvestigacionUtn", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("moneda IN ('ARS', 'USD')", name="ck_equipamiento_snapshot_moneda"),
        db.UniqueConstraint(
            "memoria_version_id",
            "equipamiento_id",
            name="uq_equipamiento_memoria_version"
        ),
    )

    def serialize(self):
        return self.to_dict()
