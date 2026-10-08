from datetime import date

from extension import db
from modules.shared.models.audit_mixin import AuditMixin

class InvestigadorProyecto(db.Model, AuditMixin):
    __tablename__ = "investigadorxproyecto"

    id = db.Column(db.Integer, primary_key=True)

    id_investigador = db.Column(db.Integer, db.ForeignKey("investigador.id"))
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyecto_investigacion.id"))
    es_coordinador = db.Column(db.Boolean, nullable=False, default=False)

    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)

    investigador = db.relationship(
        "Investigador",
        back_populates="participaciones_proyecto"
    )

    proyecto = db.relationship(
        "ProyectoInvestigacion",
        back_populates="participaciones_investigador"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "id_investigador",
            "id_proyecto",
            "deleted_at",
            name="uq_investigador_proyecto_activo"
        ),
    )


class BecarioProyecto(db.Model, AuditMixin):
    __tablename__ = "becarioxproyecto"

    id = db.Column(db.Integer, primary_key=True)

    id_becario = db.Column(
        db.Integer,
        db.ForeignKey("becario.id"),
        nullable=False
    )

    id_proyecto = db.Column(
        db.Integer,
        db.ForeignKey("proyecto_investigacion.id"),
        nullable=False
    )

    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "id_becario",
            "id_proyecto",
            "deleted_at",
            name="uq_becario_proyecto_activo"
        ),
    )

    becario = db.relationship(
        "Becario",
        back_populates="participaciones_proyecto"
    )

    proyecto = db.relationship(
        "ProyectoInvestigacion",
        back_populates="participaciones_becario"
    )


class TipoProyecto(db.Model, AuditMixin):
    __tablename__ = 'tipo_proyecto_investigacion'
    __table_args__ = (
        db.UniqueConstraint('nombre', name='uq_tipo_proyecto_nombre'),
    )
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, nullable=False)
    proyectos_investigacion = db.relationship('ProyectoInvestigacion', back_populates='tipo_proyecto')

    def serialize(self):
        return self.to_dict()


class ProyectoInvestigacion(db.Model, AuditMixin):
    __tablename__ = 'proyecto_investigacion'

    id = db.Column(db.Integer, primary_key=True)
    codigo_proyecto = db.Column(db.String(50), nullable=False)
    nombre_proyecto = db.Column(db.Text, nullable=False)
    descripcion_proyecto = db.Column(db.Text, nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False) 
    fecha_fin = db.Column(db.Date, nullable=True)
    fecha_fin_original = db.Column(db.Date, nullable=True)
    fecha_fin_prorrogada = db.Column(db.Date, nullable=True)
    prorroga_motivo = db.Column(db.Text, nullable=True)
    prorroga_by = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    prorroga_at = db.Column(db.DateTime, nullable=True)
    prorroga_usuario = db.relationship('Usuario', foreign_keys=[prorroga_by], lazy='joined')
    logros_obtenidos = db.Column(db.Text, nullable=True)
    dificultades_proyecto = db.Column(db.Text, nullable=True)
    monto_destinado = db.Column(db.Float, nullable=True)

    tipo_proyecto_id = db.Column(db.Integer, db.ForeignKey('tipo_proyecto_investigacion.id'), nullable=False)
    tipo_proyecto = db.relationship('TipoProyecto', back_populates='proyectos_investigacion')

    grupo_utn_id = db.Column(db.Integer, db.ForeignKey('grupo_utn.id'))
    grupo_utn = db.relationship('GrupoInvestigacionUtn', back_populates='proyectos_investigacion')

    fuente_financiamiento_id = db.Column(db.Integer, db.ForeignKey('fuente_financiamiento.id'))
    fuente_financiamiento = db.relationship('FuenteFinanciamiento', back_populates='proyectos_investigacion')

    # --- Relaciones (Uno-a-Muchos) ---
    distinciones = db.relationship('DistincionRecibida', back_populates='proyecto_investigacion', cascade="all, delete-orphan")

    participaciones_investigador = db.relationship(
        "InvestigadorProyecto",
        back_populates="proyecto",
        cascade="all, delete-orphan"
    )

    participaciones_becario = db.relationship(
        "BecarioProyecto",
        back_populates="proyecto",
        cascade="all, delete-orphan"
    )


    def serialize(self, cerrado_override=None):
        data = self.to_dict()
        data["fecha_fin_original"] = (self.fecha_fin_original or self.fecha_fin).isoformat() if (self.fecha_fin_original or self.fecha_fin) else None
        data["prorroga_by_nombre"] = self._get_audit_user_name(self.prorroga_usuario)
        from modules.informes.services.cierre_proyecto import tiene_informe_de_cierre
        data["cerrado"] = (bool(self.deleted_at and self.fecha_fin and self.fecha_fin <= date.today() and tiene_informe_de_cierre(self.id, self.fecha_fin, grupo_utn_id=self.grupo_utn_id))
                           if cerrado_override is None else cerrado_override)

        # Grupo
        if self.grupo_utn:
            data["grupo_utn"] = {
                "id": self.grupo_utn.id,
                "nombre": self.grupo_utn.nombre_sigla_grupo
            }
        else:
            data["grupo_utn"] = None

        # Fuente
        if self.fuente_financiamiento:
            data["fuente_financiamiento"] = {
                "id": self.fuente_financiamiento.id,
                "nombre": self.fuente_financiamiento.nombre
            }
        else:
            data["fuente_financiamiento"] = None

        # Tipo
        if self.tipo_proyecto:
            data["tipo_proyecto"] = {
                "id": self.tipo_proyecto.id,
                "nombre": self.tipo_proyecto.nombre
            }
        else:
            data["tipo_proyecto"] = None

        # Investigadores
        data["investigadores"] = []
        for p in self.participaciones_investigador:
            if p.deleted_at is None and p.investigador:
                data["investigadores"].append({
                    "id": p.investigador.id,
                    "nombre_apellido": p.investigador.nombre_apellido,
                    "es_coordinador": p.es_coordinador,
                    "activo": bool(p.investigador.activo and p.investigador.deleted_at is None),
                    "fecha_inicio": p.fecha_inicio.isoformat(),
                    "fecha_fin": p.fecha_fin.isoformat() if p.fecha_fin else None
                })

        # Becarios
        data["becarios"] = []
        for p in self.participaciones_becario:
            if p.deleted_at is None and p.becario:
                data["becarios"].append({
                    "id": p.becario.id,
                    "nombre_apellido": p.becario.nombre_apellido,
                    "fecha_inicio": p.fecha_inicio.isoformat(),
                    "fecha_fin": p.fecha_fin.isoformat() if p.fecha_fin else None
                })

        # Distinciones (blindado)
        data["distinciones"] = []
        for d in self.distinciones:
            try:
                data["distinciones"].append(d.serialize())
            except:
                pass

        return data


class ProyectoInvestigacionMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "proyecto_investigacion_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    proyecto_investigacion_id = db.Column(
        db.Integer,
        db.ForeignKey("proyecto_investigacion.id"),
        nullable=False
    )

    codigo_proyecto = db.Column(db.String(50), nullable=False)
    nombre_proyecto = db.Column(db.Text, nullable=False)
    descripcion_proyecto = db.Column(db.Text, nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    logros_obtenidos = db.Column(db.Text, nullable=True)
    dificultades_proyecto = db.Column(db.Text, nullable=True)
    monto_destinado = db.Column(db.Float, nullable=True)

    tipo_proyecto_id = db.Column(
        db.Integer,
        db.ForeignKey("tipo_proyecto_investigacion.id"),
        nullable=False
    )
    tipo_proyecto_nombre = db.Column(db.Text, nullable=True)

    grupo_utn_id = db.Column(
        db.Integer,
        db.ForeignKey("grupo_utn.id"),
        nullable=True
    )
    grupo_utn_nombre = db.Column(db.String(255), nullable=True)

    fuente_financiamiento_id = db.Column(
        db.Integer,
        db.ForeignKey("fuente_financiamiento.id"),
        nullable=True
    )
    fuente_financiamiento_nombre = db.Column(db.String(255), nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    proyecto_investigacion = db.relationship("ProyectoInvestigacion", lazy="joined")
    tipo_proyecto = db.relationship("TipoProyecto", lazy="joined")
    grupo_utn = db.relationship("GrupoInvestigacionUtn", lazy="joined")
    fuente_financiamiento = db.relationship("FuenteFinanciamiento", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "proyecto_investigacion_id",
            name="uq_proyecto_memoria_version"
        ),
    )

    def serialize(self):
        return self.to_dict()
