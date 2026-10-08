from modules.shared.models.audit_mixin import AuditMixin
from extension import db


class GrupoInvestigacionUtn(db.Model, AuditMixin):
    __tablename__ = 'grupo_utn'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    mail = db.Column(db.Text, nullable=False)
    nombre_unidad_academica = db.Column(db.Text, nullable=False)
    objetivo_desarrollo = db.Column(db.Text, nullable=False)
    nombre_sigla_grupo = db.Column(db.Text, nullable=False)

    # --- Relaciones ---
    participaciones_directivos = db.relationship('DirectivoGrupo', back_populates='grupo_utn')
    investigadores = db.relationship('Investigador', back_populates='grupo_utn')
    becarios = db.relationship('Becario', back_populates="grupo_utn")
    personal = db.relationship('Personal', back_populates="grupo_utn")
    documentacion = db.relationship('DocumentacionBibliografica', back_populates='grupo_utn')
    equipamiento = db.relationship('Equipamiento', back_populates='grupo_utn')
    proyectos_investigacion = db.relationship('ProyectoInvestigacion', back_populates='grupo_utn')
    planificaciones = db.relationship('PlanificacionGrupo', back_populates='grupo_utn')
    visitas = db.relationship('VisitaAcademica', back_populates='grupo_utn')
    registros_propiedad = db.relationship('RegistrosPropiedad', back_populates='grupo_utn')
    trabajos_revistas = db.relationship('TrabajosRevistasReferato', back_populates='grupo_utn')
    trabajos_reunion_cientifica = db.relationship('TrabajoReunionCientifica', back_populates='grupo_utn')
    erogaciones = db.relationship('Erogacion', back_populates='grupo_utn')
    transferencias_socio_productivas = db.relationship('TransferenciaSocioProductiva', back_populates='grupo_utn')
    articulos_divulgacion = db.relationship('ArticuloDivulgacion', back_populates='grupo_utn')

    # =====================================
    # SOFT DELETE EN CASCADA
    # =====================================
    def soft_delete(self, user_id: int):
        if self.deleted_at is not None:
            return  # ya eliminado

        super().soft_delete(user_id)

        relaciones = [
            self.participaciones_directivos,
            self.investigadores,
            self.becarios,
            self.personal,
            self.documentacion,
            self.equipamiento,
            self.proyectos_investigacion,
            self.planificaciones,
            self.visitas,
            self.registros_propiedad,
            self.trabajos_revistas,
            self.trabajos_reunion_cientifica,
            self.erogaciones,
            self.transferencias_socio_productivas,
            self.articulos_divulgacion,
        ]

        for relacion in relaciones:
            for obj in relacion:
                if hasattr(obj, "soft_delete") and obj.deleted_at is None:
                    obj.soft_delete(user_id)

    # =====================================
    # 🔁 RESTORE EN CASCADA
    # =====================================
    def restore(self):
        if self.deleted_at is None:
            return  # ya activo

        super().restore()

        relaciones = [
            self.participaciones_directivos,
            self.investigadores,
            self.becarios,
            self.personal,
            self.documentacion,
            self.equipamiento,
            self.proyectos_investigacion,
            self.planificaciones,
            self.visitas,
            self.registros_propiedad,
            self.trabajos_revistas,
            self.trabajos_reunion_cientifica,
            self.erogaciones,
            self.transferencias_socio_productivas,
            self.articulos_divulgacion,
        ]

        for relacion in relaciones:
            for obj in relacion:
                if hasattr(obj, "restore") and obj.deleted_at is not None:
                    obj.restore()

    # =====================================
    # SERIALIZE
    # =====================================
    def serialize(self):
        data = self.to_dict()

        data.update({
            "directivos": [
                {
                    "id": p.directivo.id,
                    "nombre_apellido": p.directivo.nombre_apellido,
                    "cargo": p.cargo.nombre if p.cargo else None,
                    "fecha_inicio": p.fecha_inicio.isoformat()
                }
                for p in self.participaciones_directivos
                if (
                    p.fecha_fin is None
                    and p.deleted_at is None
                    and p.directivo is not None
                    and p.directivo.deleted_at is None
                    and p.cargo is not None
                    and p.cargo.deleted_at is None
                )
            ],
            "cant_investigadores": len(self.investigadores),
            "cant_becarios": len(self.becarios),
            "cant_personal": len(self.personal),
            "cant_proyectos": len(self.proyectos_investigacion),
            "cant_documentacion": len(self.documentacion),
            "cant_equipamiento": len(self.equipamiento),
            "cant_erogaciones": len(self.erogaciones),
            "cant_patentes": len(self.registros_propiedad),
        })

        return data

    @classmethod
    def load(cls):
        return cls.query.first()
