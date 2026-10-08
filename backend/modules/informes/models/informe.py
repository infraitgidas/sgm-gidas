from extension import db
from modules.shared.models.audit_mixin import AuditMixin


class Informe(db.Model, AuditMixin):
    __tablename__ = "informe"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    memoria_id = db.Column(db.Integer, db.ForeignKey("memoria.id"), nullable=False, index=True)
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey("grupo_utn.id"), nullable=False, index=True)
    titulo = db.Column(db.String(200), nullable=False)
    fecha_realizacion = db.Column(db.Date, nullable=False)
    resumen = db.Column(db.Text, nullable=False)
    actividades = db.Column(db.Text, nullable=False)
    resultados = db.Column(db.Text, nullable=False)
    observaciones = db.Column(db.Text, nullable=False)
    uct_snapshot = db.Column(db.JSON, nullable=False)
    memoria = db.relationship("Memoria", lazy="joined")
    investigadores = db.relationship("InformeInvestigador", back_populates="informe", lazy="select")
    proyectos = db.relationship("InformeProyecto", back_populates="informe", lazy="select")

    __table_args__ = (
        db.CheckConstraint("tipo IN ('investigadores', 'pid', 'uct')", name="ck_informe_tipo"),
        db.Index("ix_informe_uct_tipo_fecha", "grupo_utn_id", "tipo", "fecha_realizacion"),
    )

    def serialize(self, *, detail=False):
        data = self.to_dict()
        data["periodo_inicio"] = self.memoria.periodo_inicio.isoformat()
        data["periodo_fin"] = self.memoria.periodo_fin.isoformat()
        data["autor"] = data["created_by_nombre"]
        if not detail:
            for field in ("resumen", "actividades", "resultados", "observaciones", "uct_snapshot"):
                data.pop(field, None)
        if detail:
            if self.tipo == "investigadores":
                data["investigadores"] = [item.serialize() for item in self.investigadores if item.deleted_at is None]
            elif self.tipo == "pid":
                data["proyectos"] = [item.serialize() for item in self.proyectos if item.deleted_at is None]
        return data


class InformeInvestigador(db.Model, AuditMixin):
    __tablename__ = "informe_investigador"
    id = db.Column(db.Integer, primary_key=True)
    informe_id = db.Column(db.Integer, db.ForeignKey("informe.id"), nullable=False, index=True)
    investigador_id = db.Column(db.Integer, db.ForeignKey("investigador.id"), nullable=False, index=True)
    snapshot = db.Column(db.JSON, nullable=False)
    informe = db.relationship("Informe", back_populates="investigadores")
    __table_args__ = (db.UniqueConstraint("informe_id", "investigador_id", name="uq_informe_investigador"),)

    def serialize(self):
        return {"id": self.investigador_id, "snapshot": self.snapshot}


class InformeProyecto(db.Model, AuditMixin):
    __tablename__ = "informe_proyecto"
    id = db.Column(db.Integer, primary_key=True)
    informe_id = db.Column(db.Integer, db.ForeignKey("informe.id"), nullable=False, index=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyecto_investigacion.id"), nullable=False, index=True)
    snapshot = db.Column(db.JSON, nullable=False)
    informe = db.relationship("Informe", back_populates="proyectos")
    __table_args__ = (db.UniqueConstraint("informe_id", "proyecto_id", name="uq_informe_proyecto"),)

    def serialize(self):
        return {"id": self.proyecto_id, "snapshot": self.snapshot}
