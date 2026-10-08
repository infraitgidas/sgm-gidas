from flask import Blueprint
from modules.produccion.controllers.trabajo_revista_controller import (
    TrabajosRevistasReferatoController
)
from modules.shared.services.middleware import requiere_rol

trabajos_revistas_referato_bp = Blueprint(
    "trabajos_revistas_referato",
    __name__,
    url_prefix="/trabajos-revistas"
)

@trabajos_revistas_referato_bp.route("/", methods=["GET"], strict_slashes=False)
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return TrabajosRevistasReferatoController.get_all()

@trabajos_revistas_referato_bp.route(
    "/<int:trabajo_id>", methods=["GET"], strict_slashes=False
)
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_by_id(trabajo_id):
    return TrabajosRevistasReferatoController.get_by_id(trabajo_id)

@trabajos_revistas_referato_bp.route(
    "/<int:trabajo_id>/historial", methods=["GET"], strict_slashes=False
)
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(trabajo_id):
    return TrabajosRevistasReferatoController.get_historial(trabajo_id)

@trabajos_revistas_referato_bp.route("/", methods=["POST"], strict_slashes=False)
@requiere_rol("ADMIN", "GESTOR")
def create():
    return TrabajosRevistasReferatoController.create()

@trabajos_revistas_referato_bp.route(
    "/<int:trabajo_id>", methods=["PUT"], strict_slashes=False
)
@requiere_rol("ADMIN", "GESTOR")
def update(trabajo_id):
    return TrabajosRevistasReferatoController.update(trabajo_id)

@trabajos_revistas_referato_bp.route(
    "/<int:trabajo_id>", methods=["DELETE"], strict_slashes=False
)
@requiere_rol("ADMIN", "GESTOR")
def delete(trabajo_id):
    return TrabajosRevistasReferatoController.delete(trabajo_id)

@trabajos_revistas_referato_bp.route(
    "/<int:trabajo_id>/restore", methods=["PUT"], strict_slashes=False
)
@requiere_rol("ADMIN", "GESTOR")
def restore(trabajo_id):
    return TrabajosRevistasReferatoController.restore(trabajo_id)

@trabajos_revistas_referato_bp.route(
    "/<int:trabajo_id>/autores/", methods=["DELETE"], strict_slashes=False
)
@requiere_rol("ADMIN", "GESTOR")
def remove_autores(trabajo_id):
    return TrabajosRevistasReferatoController.remove_autores(trabajo_id)
