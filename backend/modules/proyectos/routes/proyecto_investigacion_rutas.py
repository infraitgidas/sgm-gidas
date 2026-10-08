from flask import Blueprint
from modules.proyectos.controllers.proyecto_investigacion_controller import (
    ProyectoInvestigacionController
)

from modules.shared.services.middleware import requiere_rol

proyecto_investigacion_bp = Blueprint(
    "proyecto_investigacion",
    __name__,
    url_prefix="/proyectos"
)

# =========================
# CRUD 

@proyecto_investigacion_bp.route("", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return ProyectoInvestigacionController.get_all()

@proyecto_investigacion_bp.route("/<int:proyecto_id>", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_by_id(proyecto_id):
    return ProyectoInvestigacionController.get_by_id(proyecto_id)

@proyecto_investigacion_bp.route("/<int:proyecto_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(proyecto_id):
    return ProyectoInvestigacionController.get_historial(proyecto_id)

@proyecto_investigacion_bp.route("", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def create():
    return ProyectoInvestigacionController.create()

@proyecto_investigacion_bp.route("/<int:proyecto_id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def update(proyecto_id):
    return ProyectoInvestigacionController.update(proyecto_id)

@proyecto_investigacion_bp.route("/<int:proyecto_id>", methods=["DELETE"])
@requiere_rol("ADMIN", "GESTOR")
def cerrar(proyecto_id):
    return ProyectoInvestigacionController.cerrar(proyecto_id)


@proyecto_investigacion_bp.route("/<int:proyecto_id>/cerrar", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def cerrar_con_fecha(proyecto_id):
    return ProyectoInvestigacionController.cerrar_con_fecha(proyecto_id)

@proyecto_investigacion_bp.route("/<int:proyecto_id>/reabrir", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def reabrir(proyecto_id):
    return ProyectoInvestigacionController.reabrir(proyecto_id)


@proyecto_investigacion_bp.route("/<int:proyecto_id>/prorroga", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def prorrogar(proyecto_id):
    return ProyectoInvestigacionController.prorrogar(proyecto_id)

# =========================
# BECARIOS ↔ PROYECTO

@proyecto_investigacion_bp.route("/<int:proyecto_id>/becarios", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def vincular_becarios(proyecto_id):
    return ProyectoInvestigacionController.vincular_becarios(proyecto_id)

@proyecto_investigacion_bp.route("/<int:proyecto_id>/becarios", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def desvincular_becarios(proyecto_id):
    return ProyectoInvestigacionController.desvincular_becarios(proyecto_id)

# =========================
# INVESTIGADORES ↔ PROYECTO

@proyecto_investigacion_bp.route("/<int:proyecto_id>/investigadores", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def vincular_investigadores(proyecto_id):
    return ProyectoInvestigacionController.vincular_investigadores(proyecto_id)

@proyecto_investigacion_bp.route("/<int:proyecto_id>/investigadores", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def desvincular_investigadores(proyecto_id):
    return ProyectoInvestigacionController.desvincular_investigadores(proyecto_id)
