from extension import db
from modules.shared.models.audit_mixin import AuditMixin

class AdoptanteTransferencia(db.Model, AuditMixin):
    __tablename__ = 'adoptante_x_transferencia'

    id = db.Column(db.Integer, primary_key=True)

    adoptante_id = db.Column(
        db.Integer,
        db.ForeignKey('adoptante.id'),
        nullable=False
    )

    transferencia_id = db.Column(
        db.Integer,
        db.ForeignKey('transferencia_socio_productiva.id'),
        nullable=False
    )

    adoptante = db.relationship('Adoptante', back_populates='participaciones')
    transferencia = db.relationship('TransferenciaSocioProductiva', back_populates='participaciones')

    __table_args__ = (
        db.UniqueConstraint(
            "adoptante_id",
            "transferencia_id",
            "deleted_at",
            name="uq_adoptante_transferencia_activo"
        ),
    )

class Adoptante(db.Model, AuditMixin):
    __tablename__ = 'adoptante'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey("grupo_utn.id"), nullable=True, index=True)
    nombre = db.Column(db.Text, nullable=False)
    
    participaciones = db.relationship(
        'AdoptanteTransferencia',
        back_populates='adoptante'
    )

    def serialize(self):
        return self.to_dict()

class TransferenciaSocioProductiva(db.Model, AuditMixin):
    __tablename__ = 'transferencia_socio_productiva'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    numero_transferencia = db.Column(db.Integer, nullable=False, unique=True)
    denominacion = db.Column(db.Text, nullable=False)
    demandante = db.Column(db.Text, nullable=False)
    descripcion_actividad = db.Column(db.Text, nullable=False)
    monto = db.Column(db.Float, nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    
    participaciones = db.relationship(
        'AdoptanteTransferencia',
        back_populates='transferencia'
    )
    
    tipo_contrato_id = db.Column(db.Integer, db.ForeignKey('tipo_contrato_transferencia.id'), nullable=False)
    tipo_contrato_transferencia = db.relationship('TipoContrato', back_populates='transferencias')

    grupo_utn_id = db.Column(db.Integer, db.ForeignKey('grupo_utn.id'), nullable=False)
    grupo_utn = db.relationship('GrupoInvestigacionUtn', back_populates='transferencias_socio_productivas')

    @property
    def adoptante(self):
        return ", ".join(
            p.adoptante.nombre
            for p in self.participaciones
            if p.deleted_at is None and p.adoptante
        )

    def serialize(self):
        data = self.to_dict()
        data["tipo_contrato"] = (
            self.tipo_contrato_transferencia.nombre if self.tipo_contrato_transferencia else None
        )
        data["adoptantes"] = [
        {
            "id": p.adoptante.id,
            "nombre": p.adoptante.nombre
        }
        for p in self.participaciones
        if p.deleted_at is None
]
        data["grupo"] = (
            self.grupo_utn.nombre_sigla_grupo if self.grupo_utn else None
        )

        return data


class TransferenciaSocioProductivaMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "transferencia_socio_productiva_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    transferencia_id = db.Column(
        db.Integer,
        db.ForeignKey("transferencia_socio_productiva.id"),
        nullable=False
    )

    numero_transferencia = db.Column(db.Integer, nullable=False)
    denominacion = db.Column(db.Text, nullable=False)
    demandante = db.Column(db.Text, nullable=False)
    descripcion_actividad = db.Column(db.Text, nullable=False)
    monto = db.Column(db.Float, nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)

    tipo_contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("tipo_contrato_transferencia.id"),
        nullable=False
    )
    tipo_contrato_nombre = db.Column(db.Text, nullable=True)

    grupo_utn_id = db.Column(
        db.Integer,
        db.ForeignKey("grupo_utn.id"),
        nullable=False
    )
    grupo_utn_nombre = db.Column(db.String(255), nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    transferencia = db.relationship("TransferenciaSocioProductiva", lazy="joined")
    tipo_contrato = db.relationship("TipoContrato", lazy="joined")
    grupo_utn = db.relationship("GrupoInvestigacionUtn", lazy="joined")
    adoptantes_snapshot = db.relationship(
        "AdoptanteTransferenciaMemoriaVersion",
        back_populates="transferencia_memoria_version",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "transferencia_id",
            name="uq_transferencia_memoria_version"
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["adoptantes"] = [
            item.serialize()
            for item in self.adoptantes_snapshot
            if item.deleted_at is None
        ]
        return data


class AdoptanteTransferenciaMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "adoptante_transferencia_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    transferencia_memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("transferencia_socio_productiva_memoria_version.id"),
        nullable=False
    )
    adoptante_transferencia_id = db.Column(
        db.Integer,
        db.ForeignKey("adoptante_x_transferencia.id"),
        nullable=False
    )
    adoptante_id = db.Column(
        db.Integer,
        db.ForeignKey("adoptante.id"),
        nullable=False
    )
    adoptante_nombre = db.Column(db.Text, nullable=True)

    transferencia_memoria_version = db.relationship(
        "TransferenciaSocioProductivaMemoriaVersion",
        back_populates="adoptantes_snapshot",
        lazy="joined"
    )
    adoptante_transferencia = db.relationship("AdoptanteTransferencia", lazy="joined")
    adoptante = db.relationship("Adoptante", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "transferencia_memoria_version_id",
            "adoptante_transferencia_id",
            name="uq_adoptante_transferencia_memoria_version"
        ),
    )

    def serialize(self):
        return self.to_dict()


class TipoContrato(db.Model, AuditMixin):
    __tablename__ = 'tipo_contrato_transferencia'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = db.Column(db.Text, nullable=False)

    transferencias = db.relationship('TransferenciaSocioProductiva', back_populates='tipo_contrato_transferencia')

    def serialize(self):
        return self.to_dict()
