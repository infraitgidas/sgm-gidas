import enum
from extension import db
from modules.shared.models.audit_mixin import AuditMixin


class EstadoMemoria(enum.Enum):
    ABIERTA = "abierta"
    EN_REVISION = "en revision"
    CERRADA = "cerrada"


class Memoria(db.Model, AuditMixin):
    __tablename__ = "memoria"

    id = db.Column(db.Integer, primary_key=True)
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey("grupo_utn.id"), nullable=True, index=True)
    grupo_utn = db.relationship("GrupoInvestigacionUtn", lazy="joined")
    periodo_inicio = db.Column(db.Date, nullable=False)
    periodo_fin = db.Column(db.Date, nullable=False)
    version_actual_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=True
    )

    versiones = db.relationship(
        "MemoriaVersion",
        back_populates="memoria",
        foreign_keys="MemoriaVersion.memoria_id",
        cascade="all, delete-orphan",
        order_by="MemoriaVersion.numero_version"
    )

    version_actual = db.relationship(
        "MemoriaVersion",
        foreign_keys=[version_actual_id],
        post_update=True
    )

    def serialize(self):
        data = self.to_dict()
        data["version_actual"] = (
            self.version_actual.serialize()
            if self.version_actual else None
        )
        data["cantidad_versiones"] = len(self.versiones)
        data["grupo_utn_nombre"] = self.grupo_utn.nombre_sigla_grupo if self.grupo_utn else None
        return data


class MemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "memoria_version"

    id = db.Column(db.Integer, primary_key=True)
    numero_version = db.Column(db.Integer, nullable=False)
    contexto_institucional = db.Column(db.JSON, nullable=True)
    # La apertura pertenece a la vida de esta version concreta. Puede ser
    # informada por el usuario al crearla o resolverse desde la capa de servicio.
    fecha_apertura = db.Column(db.DateTime, nullable=False)
    # La fecha de cierre se completa cuando la version deja de estar activa
    # por cambio a cerrada o por la logica de versionado definida en servicios.
    fecha_cierre = db.Column(db.DateTime, nullable=True)
    estado = db.Column(
        db.Enum(
            EstadoMemoria,
            values_callable=lambda estados: [estado.value for estado in estados],
            native_enum=False,
            name="estado_memoria_enum"
        ),
        nullable=False,
        default=EstadoMemoria.ABIERTA
    )
    memoria_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria.id"),
        nullable=False
    )

    memoria = db.relationship(
        "Memoria",
        back_populates="versiones",
        foreign_keys=[memoria_id]
    )

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_id",
            "numero_version",
            name="uq_memoria_version_numero"
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["contexto_institucional"] = self.contexto_institucional_seguro()
        data["estado"] = self.estado.value if self.estado else None
        return data

    def contexto_institucional_seguro(self):
        contexto = self.contexto_institucional
        grupo = contexto.get("grupo") if isinstance(contexto, dict) else None
        if not isinstance(grupo, dict) or self.memoria is None:
            return None
        return contexto if grupo.get("id") == self.memoria.grupo_utn_id else None
