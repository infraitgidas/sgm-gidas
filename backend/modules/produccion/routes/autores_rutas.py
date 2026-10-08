from flask import Blueprint
from modules.produccion.controllers.autores_controller import AutorController
from modules.shared.services.middleware import requiere_rol

autor_bp = Blueprint(
    "autor",
    __name__,
    url_prefix="/autores"
)

# ==========================================
# CONSULTAS
# ==========================================

@autor_bp.route("/", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return AutorController.get_all()


@autor_bp.route("/<int:autor_id>", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_by_id(autor_id):
    return AutorController.get_by_id(autor_id)


@autor_bp.route("/<int:autor_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(autor_id):
    return AutorController.get_historial(autor_id)


# ==========================================
# MODIFICACIONES
# ==========================================

@autor_bp.route("/", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def create():
    return AutorController.create()


@autor_bp.route("/<int:autor_id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def update(autor_id):
    return AutorController.update(autor_id)


@autor_bp.route("/<int:autor_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def delete(autor_id):
    return AutorController.delete(autor_id)


# ==========================================
# RELACIÓN AUTOR - LIBRO
# ==========================================

@autor_bp.route("/<int:autor_id>/libros", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def add_libro(autor_id):
    return AutorController.add_libro(autor_id)


@autor_bp.route("/<int:autor_id>/libros/<int:libro_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def remove_libro(autor_id, libro_id):
    return AutorController.remove_libro(autor_id, libro_id)
