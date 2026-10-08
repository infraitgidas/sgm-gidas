import datetime
import re
from sqlalchemy.orm import validates
from extension import db
from modules.produccion.models.trabajo_autor import TrabajoRevistaAutor
from modules.shared.models.audit_mixin import AuditMixin


class TipoRevista(db.Model, AuditMixin):
    __tablename__ = "tipo_revista"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)

    trabajos_revistas = db.relationship(
        "TrabajosRevistasReferato",
        back_populates="tipo_revista",
        lazy="select",
    )

    def serialize(self):
        return self.to_dict()



class TrabajosRevistasReferato(db.Model, AuditMixin):
    __tablename__ = 'trabajos_revista'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)

    enlace = db.Column(db.String(2048), nullable=True)
    titulo_trabajo = db.Column(db.Text, nullable=False)
    nombre_revista = db.Column(db.Text, nullable=False)
    editorial = db.Column(db.Text, nullable=False)
    issn = db.Column(db.Text, nullable=False)
    pais = db.Column(db.Text, nullable=False)
    fecha_publicacion = db.Column(db.Date, nullable=False)

    grupo_utn_id = db.Column(
        db.Integer,
        db.ForeignKey('grupo_utn.id')
    )

    grupo_utn = db.relationship(
        'GrupoInvestigacionUtn',
        back_populates='trabajos_revistas'
    )

    tipo_revista_id = db.Column(
        db.Integer,
        db.ForeignKey('tipo_revista.id'),
        nullable=False
    )

    tipo_revista = db.relationship(
        'TipoRevista',
        back_populates='trabajos_revistas'
    )

    autorias = db.relationship(
        "TrabajoRevistaAutor", back_populates="trabajo", cascade="all, delete-orphan", lazy="selectin"
    )

    def serialize(self):
        data = self.to_dict()

        data.update({
            "grupo": (
                self.grupo_utn.nombre_sigla_grupo
                if self.grupo_utn else None
            ),
            "autores": [autor.serialize() for autor in self.autorias],
            "tipo_revista": (
                {
                    "id": self.tipo_revista.id,
                    "nombre": self.tipo_revista.nombre
                }
                if self.tipo_revista else None
            )
        })

        return data


class TrabajosRevistasReferatoMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "trabajos_revista_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    trabajo_revista_id = db.Column(
        db.Integer,
        db.ForeignKey("trabajos_revista.id"),
        nullable=False
    )

    enlace = db.Column(db.String(2048), nullable=True)
    titulo_trabajo = db.Column(db.Text, nullable=False)
    nombre_revista = db.Column(db.Text, nullable=False)
    editorial = db.Column(db.Text, nullable=False)
    issn = db.Column(db.Text, nullable=False)
    pais = db.Column(db.Text, nullable=False)
    fecha_publicacion = db.Column(db.Date, nullable=False)

    grupo_utn_id = db.Column(
        db.Integer,
        db.ForeignKey("grupo_utn.id"),
        nullable=True
    )
    grupo_utn_nombre = db.Column(db.String(255), nullable=True)

    tipo_revista_id = db.Column(
        db.Integer,
        db.ForeignKey("tipo_revista.id"),
        nullable=False
    )
    tipo_revista_nombre = db.Column(db.String(100), nullable=True)
    autores = db.Column(db.JSON, nullable=False, default=list)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    trabajo_revista = db.relationship("TrabajosRevistasReferato", lazy="joined")
    grupo_utn = db.relationship("GrupoInvestigacionUtn", lazy="joined")
    tipo_revista_rel = db.relationship("TipoRevista", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "trabajo_revista_id",
            name="uq_trabajo_revista_memoria_version"
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["autores"] = self.autores or []
        return data
    

