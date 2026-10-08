from flask import Blueprint

from modules.informes.controllers.informe_controller import InformeController
from modules.shared.services.middleware import requiere_rol


informe_bp = Blueprint("informe", __name__, url_prefix="/informes")


@informe_bp.route("/<tipo>/candidatos", methods=["GET"])
@requiere_rol("GESTOR")
def candidates_informe(tipo):
    return InformeController.candidates(tipo)


@informe_bp.route("/<tipo>", methods=["GET"])
@requiere_rol("GESTOR")
def list_informes(tipo):
    return InformeController.list(tipo)


@informe_bp.route("/<tipo>", methods=["POST"])
@requiere_rol("GESTOR")
def create_informe(tipo):
    return InformeController.create(tipo)


@informe_bp.route("/<tipo>/<int:informe_id>", methods=["GET"])
@requiere_rol("GESTOR")
def get_informe(tipo, informe_id):
    return InformeController.get(tipo, informe_id)


@informe_bp.route("/<tipo>/<int:informe_id>", methods=["PUT"])
@requiere_rol("GESTOR")
def update_informe(tipo, informe_id):
    return InformeController.update(tipo, informe_id)


@informe_bp.route("/<tipo>/<int:informe_id>", methods=["DELETE"])
@requiere_rol("GESTOR")
def delete_informe(tipo, informe_id):
    return InformeController.delete(tipo, informe_id)


@informe_bp.route("/<tipo>/<int:informe_id>/historial", methods=["GET"])
@requiere_rol("GESTOR")
def history_informe(tipo, informe_id):
    return InformeController.history(tipo, informe_id)
