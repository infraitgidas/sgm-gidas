"""Identidad documental compartida por las variantes de Personal."""

from extension import db


class IdentidadPersonal(db.Model):
    __tablename__ = "identidad_personal"

    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(8), nullable=False, unique=True)
    cuil = db.Column(db.String(13), nullable=False, unique=True)
