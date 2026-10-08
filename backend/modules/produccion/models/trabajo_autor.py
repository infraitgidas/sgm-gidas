"""Autoría de investigadores y becarios con integridad referencial."""
from sqlalchemy.orm import declared_attr

from extension import db


class TrabajoAutorMixin:
    id = db.Column(db.Integer, primary_key=True)
    investigador_id = db.Column(db.Integer, db.ForeignKey("investigador.id", ondelete="RESTRICT"), index=True)
    becario_id = db.Column(db.Integer, db.ForeignKey("becario.id", ondelete="RESTRICT"), index=True)

    @declared_attr
    def investigador(cls):
        return db.relationship("Investigador", lazy="joined")

    @declared_attr
    def becario(cls):
        return db.relationship("Becario", lazy="joined")

    @property
    def integrante(self):
        return self.investigador or self.becario

    @property
    def rol(self):
        if self.investigador_id is not None:
            return "investigador"
        return "becario"

    def serialize(self):
        persona = self.integrante
        tipo = {"investigador": "Investigador", "becario": "Becario"}[self.rol]
        return {"id": persona.id, "rol": self.rol, "tipo": tipo,
                "nombre_apellido": persona.nombre_apellido,
                "activo": persona.activo and persona.deleted_at is None}


def restricciones_autoria(tabla):
    return (
        db.CheckConstraint(
            "(CASE WHEN investigador_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN becario_id IS NULL THEN 0 ELSE 1 END) = 1",
            name=f"ck_{tabla}_un_integrante"),
        *(db.UniqueConstraint("trabajo_id", f"{rol}_id", name=f"uq_{tabla}_{rol}")
          for rol in ("investigador", "becario")),
    )


class TrabajoReunionAutor(db.Model, TrabajoAutorMixin):
    __tablename__ = "trabajo_reunion_autor"
    trabajo_id = db.Column(db.Integer, db.ForeignKey("trabajo_reunion_cientifica.id", ondelete="CASCADE"), nullable=False, index=True)
    trabajo = db.relationship("TrabajoReunionCientifica", back_populates="autorias")
    __table_args__ = restricciones_autoria(__tablename__)


class TrabajoRevistaAutor(db.Model, TrabajoAutorMixin):
    __tablename__ = "trabajo_revista_autor"
    trabajo_id = db.Column(db.Integer, db.ForeignKey("trabajos_revista.id", ondelete="CASCADE"), nullable=False, index=True)
    trabajo = db.relationship("TrabajosRevistasReferato", back_populates="autorias")
    __table_args__ = restricciones_autoria(__tablename__)
