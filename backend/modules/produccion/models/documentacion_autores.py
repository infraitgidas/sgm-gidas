import datetime
from extension import db
from modules.shared.models.audit_mixin import AuditMixin

autor_libro = db.Table('autorxlibro', 
                       db.Column('id_autor', db.Integer, db.ForeignKey('autor.id'), primary_key=True),
                       db.Column('id_libro', db.Integer, db.ForeignKey('documentacion_bibliografica.id'), primary_key=True)
)

class DocumentacionBibliografica(db.Model, AuditMixin):
    __tablename__ = 'documentacion_bibliografica'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.Text, nullable=False)
    editorial = db.Column(db.Text, nullable=False)
    anio = db.Column(db.Integer, nullable=False)

    grupo_id = db.Column(
        db.Integer,
        db.ForeignKey('grupo_utn.id'),
        nullable=False
    )

    fecha = db.Column(
        db.Date,
        default=datetime.date.today, 
        nullable=False
    )

    grupo_utn = db.relationship(
        'GrupoInvestigacionUtn',
        back_populates='documentacion'
    )

    autores = db.relationship(
        "Autor",
        secondary=autor_libro,
        back_populates="libros"
    )

    def serialize(self):
        data = self.to_dict()

        data.update({
            "grupo": self.grupo_utn.nombre_unidad_academica if self.grupo_utn else None,
            "autores": [
                {
                    "id": a.id,
                    "nombre_apellido": a.nombre_apellido
                }
                for a in self.autores
                if not hasattr(a, "deleted_at") or a.deleted_at is None
            ]
        })

        return data

    
    
class Autor(db.Model, AuditMixin):
    __tablename__ = 'autor'
    id = db.Column(db.Integer, primary_key=True)
    grupo_utn_id = db.Column(db.Integer, db.ForeignKey("grupo_utn.id"), nullable=True, index=True)
    nombre_apellido = db.Column(db.Text, nullable=False)  
    libros = db.relationship("DocumentacionBibliografica", secondary=autor_libro, back_populates="autores")
    
    def serialize(self):
        data = self.to_dict()
        data["libros"] = [
            {"id": a.id, "titulo": a.titulo}
            for a in self.libros
        ]
        
        return data


class DocumentacionBibliograficaMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "documentacion_bibliografica_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("memoria_version.id"),
        nullable=False
    )
    documentacion_bibliografica_id = db.Column(
        db.Integer,
        db.ForeignKey("documentacion_bibliografica.id"),
        nullable=False
    )

    titulo = db.Column(db.Text, nullable=False)
    editorial = db.Column(db.Text, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    grupo_id = db.Column(
        db.Integer,
        db.ForeignKey("grupo_utn.id"),
        nullable=False
    )
    grupo_nombre = db.Column(db.String(255), nullable=True)

    memoria_version = db.relationship("MemoriaVersion", lazy="joined")
    documentacion_bibliografica = db.relationship(
        "DocumentacionBibliografica",
        lazy="joined"
    )
    grupo_utn = db.relationship("GrupoInvestigacionUtn", lazy="joined")
    autores_snapshot = db.relationship(
        "DocumentacionBibliograficaAutorMemoriaVersion",
        back_populates="documentacion_memoria_version",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "memoria_version_id",
            "documentacion_bibliografica_id",
            name="uq_documentacion_memoria_version"
        ),
    )

    def serialize(self):
        data = self.to_dict()
        data["autores"] = [
            item.serialize() for item in self.autores_snapshot
            if item.deleted_at is None
        ]
        return data


class DocumentacionBibliograficaAutorMemoriaVersion(db.Model, AuditMixin):
    __tablename__ = "documentacion_bibliografica_autor_memoria_version"

    id = db.Column(db.Integer, primary_key=True)

    documentacion_memoria_version_id = db.Column(
        db.Integer,
        db.ForeignKey("documentacion_bibliografica_memoria_version.id"),
        nullable=False
    )
    autor_id = db.Column(
        db.Integer,
        db.ForeignKey("autor.id"),
        nullable=False
    )
    nombre_apellido = db.Column(db.Text, nullable=False)

    documentacion_memoria_version = db.relationship(
        "DocumentacionBibliograficaMemoriaVersion",
        back_populates="autores_snapshot",
        lazy="joined"
    )
    autor = db.relationship("Autor", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint(
            "documentacion_memoria_version_id",
            "autor_id",
            name="uq_documentacion_autor_memoria_version"
        ),
    )

    def serialize(self):
        return self.to_dict()
        
        
