from flask import Blueprint, request
from modules.personal.controllers.personal_controller import PersonalController
from modules.personal.controllers.personal_completo_controller import PersonalCompletoController
from modules.shared.services.middleware import requiere_rol

personal_bp = Blueprint(
    "personal",
    __name__,
    url_prefix="/personal"
)

@personal_bp.route("", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def crear():
    return PersonalController.crear(request)

@personal_bp.route("", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def listar():
    return PersonalController.listar(request)

@personal_bp.route("/all", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def listar_completo():
    return PersonalCompletoController.listar()

@personal_bp.route("/<string:rol>/<int:id>", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def obtener(rol, id):
    return PersonalController.obtener_por_id(request, rol, id)

@personal_bp.route("/<string:rol>/<int:id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def obtener_historial(rol, id):
    return PersonalController.obtener_historial(request, rol, id)

@personal_bp.route("/<string:rol>/<int:id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def actualizar(rol, id):
    return PersonalController.actualizar(request, rol, id)

@personal_bp.route("/<string:rol>/<int:id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def eliminar(rol, id):
    return PersonalController.eliminar(request, rol, id)
