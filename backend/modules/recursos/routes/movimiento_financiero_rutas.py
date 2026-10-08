from flask import Blueprint

from modules.recursos.controllers.movimiento_financiero_controller import MovimientoFinancieroController
from modules.shared.services.middleware import requiere_rol


movimiento_financiero_bp = Blueprint(
    "movimiento_financiero", __name__, url_prefix="/movimientos"
)


@movimiento_financiero_bp.route("/", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return MovimientoFinancieroController.get_all()


@movimiento_financiero_bp.route("/categorias", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_categorias():
    return MovimientoFinancieroController.get_categorias()


@movimiento_financiero_bp.route("/cotizacion", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_cotizacion():
    return MovimientoFinancieroController.get_cotizacion()


@movimiento_financiero_bp.route("/grupos/<int:grupo_id>/resumen", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_resumen(grupo_id):
    return MovimientoFinancieroController.get_resumen(grupo_id)


@movimiento_financiero_bp.route("/grupos/<int:grupo_id>/saldos-por-fuente", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_saldos_por_fuente(grupo_id):
    return MovimientoFinancieroController.get_saldos_por_fuente(grupo_id)


@movimiento_financiero_bp.route("/grupos/<int:grupo_id>/equipamientos-disponibles", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_equipamientos_disponibles(grupo_id):
    return MovimientoFinancieroController.get_equipamientos_disponibles(grupo_id)


@movimiento_financiero_bp.route("/<int:movimiento_id>", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_by_id(movimiento_id):
    return MovimientoFinancieroController.get_by_id(movimiento_id)


@movimiento_financiero_bp.route("/<int:movimiento_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(movimiento_id):
    return MovimientoFinancieroController.get_historial(movimiento_id)


@movimiento_financiero_bp.route("/", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def create():
    return MovimientoFinancieroController.create()


@movimiento_financiero_bp.route("/<int:movimiento_id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def update(movimiento_id):
    return MovimientoFinancieroController.update(movimiento_id)


@movimiento_financiero_bp.route("/<int:movimiento_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def delete(movimiento_id):
    return MovimientoFinancieroController.delete(movimiento_id)
