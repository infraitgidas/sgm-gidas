from flask import Blueprint

from modules.produccion.controllers.tipo_revista_controller import TipoRevistaController
from modules.shared.services.middleware import requiere_rol


tipo_revista_bp = Blueprint(
    "tipo_revista",
    __name__,
    url_prefix="/tipos-revista",
)


@tipo_revista_bp.route("/", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return TipoRevistaController.get_all()


@tipo_revista_bp.route("/<int:tipo_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(tipo_id):
    return TipoRevistaController.get_historial(tipo_id)


@tipo_revista_bp.route("/", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def create():
    return TipoRevistaController.create()


@tipo_revista_bp.route("/<int:tipo_id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def update(tipo_id):
    return TipoRevistaController.update(tipo_id)


@tipo_revista_bp.route("/<int:tipo_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def delete(tipo_id):
    return TipoRevistaController.delete(tipo_id)
