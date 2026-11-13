from datetime import date

from extension import db
from modules.shared.models.audit_mixin import AuditMixin

class ActividadDocencia(db.Model, AuditMixin):
    __tablename__ = 'actividad_y_catedra_posgrado'

    id = db.Column(db.Integer, primary_key=True)

    curso = db.Column(db.Text, nullable=False)
    institucion = db.Column(db.Text, nullable=False)

    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)

    investigador_id = db.Column(
        db.Integer,
        db.ForeignKey('investigador.id'),
        nullable=False
    )
    
    investigador = db.relationship(
    "Investigador",
    back_populates="actividades_docencia"
    )

    investigadores_grado = db.relationship(
        "InvestigadorActividadGrado",
        back_populates="actividad_docencia",
        cascade="all, delete-orphan"
    )
        
    rol_actividad_id = db.Column(
        db.Integer,
        db.ForeignKey('rol_actividad_docencia.id')
    )

    rol_actividad = db.relationship(
        'RolActividad',
        back_populates='actividades_docencia'
    )

    @staticmethod
    def _serializar_grado_historial(historial):
        data = historial.to_dict()
        data["grado_academico"] = (
            {
                "id": historial.grado_academico.id,
                "nombre": historial.grado_academico.nombre
            }
            if historial.grado_academico else None
        )
        data["activo"] = historial.fecha_fin is None
        return data

    def serialize(self):
        data = self.to_dict()

        historial_ordenado = sorted(
            self.investigadores_grado,
            key=lambda h: (
                h.fecha_inicio or date.min,
                h.id or 0
            ),
            reverse=True
        )
        historial_activo = next(
            (h for h in historial_ordenado if h.fecha_fin is None),
            None
        )
        grado_activo = historial_activo.grado_academico if historial_activo else None

        data.update({
            "investigador": (
                {
                    "id": self.investigador.id,
                    "nombre_apellido": self.investigador.nombre_apellido
                }
                if self.investigador and self.investigador.deleted_at is None
                else None
            ),
            "grado_academico": (
                {
                    "id": grado_activo.id,
                    "nombre": grado_activo.nombre
                }
                if grado_activo else None
            ),
            "grado_academico_actual": (
                {
                    "id": grado_activo.id,
                    "nombre": grado_activo.nombre
                }
                if grado_activo else None
            ),
            "rol_actividad": (
                {
                    "id": self.rol_actividad.id,
                    "nombre": self.rol_actividad.nombre
                }
                if self.rol_actividad else None
            ),
            "historial_grados": [
                ActividadDocencia._serializar_grado_historial(h)
                for h in historial_ordenado
            ]
        })

        return data



class RolActividad(db.Model, AuditMixin):
    __tablename__ = 'rol_actividad_docencia'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)

    actividades_docencia = db.relationship(
        'ActividadDocencia',
        back_populates='rol_actividad',
        lazy='select'
    )

    def serialize(self):
        return self.to_dict()
        
        
class GradoAcademico(db.Model, AuditMixin):
    __tablename__ = 'grado_academico'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)

    participaciones = db.relationship(
        "InvestigadorActividadGrado",
        back_populates="grado_academico",
        cascade="all, delete-orphan"
    )

    def serialize(self):
        return self.to_dict()
        
        
class InvestigadorActividadGrado(db.Model, AuditMixin):
    __tablename__ = "investigador_actividad_grado"

    id = db.Column(db.Integer, primary_key=True)

    investigador_id = db.Column(
        db.Integer,
        db.ForeignKey("investigador.id"),
        nullable=False
    )

    actividad_docencia_id = db.Column(
        db.Integer,
        db.ForeignKey("actividad_y_catedra_posgrado.id"),
        nullable=False
    )

    grado_academico_id = db.Column(
        db.Integer,
        db.ForeignKey("grado_academico.id"),
        nullable=False
    )

    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)

    investigador = db.relationship(
        "Investigador",
        back_populates="grados_actividad"
    )

    actividad_docencia = db.relationship(
        "ActividadDocencia",
        back_populates="investigadores_grado"
    )

    grado_academico = db.relationship(
        "GradoAcademico",
        back_populates="participaciones"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "investigador_id",
            "actividad_docencia_id",
            "grado_academico_id",
            "fecha_inicio",
            name="uq_hist_grado_actividad"
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["grado_academico"] = (
            {
                "id": self.grado_academico.id,
                "nombre": self.grado_academico.nombre
            }
            if self.grado_academico else None
        )
        data["activo"] = self.fecha_fin is None
        return data


class ActividadDocenciaMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "actividad_docencia_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    actividad_docencia_id = db.Column(
        db.Integer,
        db.ForeignKey("actividad_y_catedra_posgrado.id"),
        nullable=False
    )

    curso = db.Column(db.Text, nullable=False)
    institucion = db.Column(db.Text, nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)

    investigador_id = db.Column(
        db.Integer,
        db.ForeignKey("investigador.id"),
        nullable=False
    )
    investigador_nombre = db.Column(db.String(255), nullable=True)

    rol_actividad_id = db.Column(
        db.Integer,
        db.ForeignKey("rol_actividad_docencia.id"),
        nullable=True
    )
    rol_actividad_nombre = db.Column(db.String(255), nullable=True)

    grado_academico_id = db.Column(
        db.Integer,
        db.ForeignKey("grado_academico.id"),
        nullable=True
    )
    grado_academico_nombre = db.Column(db.String(255), nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    actividad_docencia = db.relationship("ActividadDocencia", lazy="joined")
    investigador = db.relationship("Investigador", lazy="joined")
    rol_actividad = db.relationship("RolActividad", lazy="joined")
    grado_academico = db.relationship("GradoAcademico", lazy="joined")
    historial_grados = db.relationship(
        "ActividadDocenciaGradoMemoriaVersion",
        back_populates="actividad_docencia_memoria_version",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "actividad_docencia_id",
            name="uq_actividad_docencia_memoria_version"
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["historial_grados"] = [
            item.serialize() for item in sorted(
                self.historial_grados,
                key=lambda item: (
                    item.fecha_inicio or date.min,
                    item.id or 0
                ),
                reverse=True
            )
            if item.deleted_at is None
        ]
        return data


class ActividadDocenciaGradoMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "actividad_docencia_grado_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    actividad_docencia_memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("actividad_docencia_memoria_version.id"),
        nullable=False
    )
    investigador_actividad_grado_id = db.Column(
        db.Integer,
        db.ForeignKey("investigador_actividad_grado.id"),
        nullable=False
    )

    investigador_id = db.Column(
        db.Integer,
        db.ForeignKey("investigador.id"),
        nullable=False
    )
    grado_academico_id = db.Column(
        db.Integer,
        db.ForeignKey("grado_academico.id"),
        nullable=False
    )
    grado_academico_nombre = db.Column(db.String(255), nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)

    actividad_docencia_memoria_version = db.relationship(
        "ActividadDocenciaMemoriaVersion",
        back_populates="historial_grados",
        lazy="joined"
    )
    investigador_actividad_grado = db.relationship(
        "InvestigadorActividadGrado",
        lazy="joined"
    )
    investigador = db.relationship("Investigador", lazy="joined")
    grado_academico = db.relationship("GradoAcademico", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "actividad_docencia_memoria_version_id",
            "investigador_actividad_grado_id",
            name="uq_actividad_docencia_grado_memoria_version"
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["activo"] = self.fecha_fin is None
        return data
