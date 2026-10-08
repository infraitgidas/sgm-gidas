from flask import Blueprint

from modules.grupo.controllers.tipo_visita_controller import TipoVisitaController
from modules.shared.services.middleware import requiere_rol


tipo_visita_bp = Blueprint(
    "tipo_visita",
    __name__,
    url_prefix="/tipos-visita",
)


@tipo_visita_bp.route("/", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return TipoVisitaController.get_all()


@tipo_visita_bp.route("/<int:tipo_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(tipo_id):
    return TipoVisitaController.get_historial(tipo_id)


@tipo_visita_bp.route("/", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def create():
    return TipoVisitaController.create()


@tipo_visita_bp.route("/<int:tipo_id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def update(tipo_id):
    return TipoVisitaController.update(tipo_id)


@tipo_visita_bp.route("/<int:tipo_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def delete(tipo_id):
    return TipoVisitaController.delete(tipo_id)
