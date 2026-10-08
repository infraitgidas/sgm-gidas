from flask import Blueprint
from modules.transferencia.controllers.adoptante_controller import AdoptanteController
from modules.shared.services.middleware import requiere_rol

adoptante_bp = Blueprint(
    "adoptante",
    __name__,
    url_prefix="/adoptantes"
)

# -------------------------
# GET (puede ser público o lectura)
# -------------------------
adoptante_bp.route("", methods=["GET"])(
    requiere_rol("ADMIN", "GESTOR", "LECTURA")(AdoptanteController.get_all)
)

adoptante_bp.route("/<int:adoptante_id>", methods=["GET"])(
    requiere_rol("ADMIN", "GESTOR", "LECTURA")(AdoptanteController.get_by_id)
)

adoptante_bp.route("/<int:adoptante_id>/historial", methods=["GET"])(
    requiere_rol("ADMIN", "GESTOR", "LECTURA")(AdoptanteController.get_historial)
)

# -------------------------
# CREATE
# -------------------------
adoptante_bp.route("", methods=["POST"])(
    requiere_rol("ADMIN", "GESTOR")(AdoptanteController.create)
)

# -------------------------
# UPDATE
# -------------------------
adoptante_bp.route("/<int:adoptante_id>", methods=["PUT"])(
    requiere_rol("ADMIN", "GESTOR")(AdoptanteController.update)
)

# -------------------------
# DELETE
# -------------------------
adoptante_bp.route("/<int:adoptante_id>", methods=["DELETE"])(
    requiere_rol("ADMIN", "GESTOR")(AdoptanteController.delete)
)
