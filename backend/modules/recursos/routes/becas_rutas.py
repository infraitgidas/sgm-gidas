from flask import Blueprint
from modules.recursos.controllers.becas_controller import BecaController
from modules.shared.services.middleware import requiere_rol

beca_bp = Blueprint("beca", __name__, url_prefix="/becas")

@beca_bp.route("/proximas-a-vencer", methods=["GET"])
@requiere_rol("GESTOR")
def proximas_a_vencer():
    return BecaController.proximas_a_vencer()


# =========================
# LECTURA (admin, gestor, lectura)
# =========================

@beca_bp.route("/", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return BecaController.get_all()


@beca_bp.route("/<int:beca_id>", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_by_id(beca_id):
    return BecaController.get_by_id(beca_id)


@beca_bp.route("/<int:beca_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(beca_id):
    return BecaController.get_historial(beca_id)


@beca_bp.route("/<int:beca_id>/becarios", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_becarios(beca_id):
    return BecaController.get_becarios(beca_id)


@beca_bp.route("/activas", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_activas():
    return BecaController.get_activas()


@beca_bp.route("/dashboard", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def dashboard():
    return BecaController.dashboard()


# =========================
# MODIFICACIÓN (admin, gestor)
# =========================

@beca_bp.route("/", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def create():
    return BecaController.create()


@beca_bp.route("/<int:beca_id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def update(beca_id):
    return BecaController.update(beca_id)


@beca_bp.route("/<int:beca_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def delete(beca_id):
    return BecaController.delete(beca_id)


@beca_bp.route("/<int:beca_id>/vincular-becario", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def vincular_becario(beca_id):
    return BecaController.vincular_becario(beca_id)


@beca_bp.route("/<int:beca_id>/becarios/<int:becario_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def desvincular_becario(beca_id, becario_id):
    return BecaController.desvincular_becario(beca_id, becario_id)
