from flask import Blueprint, current_app
from extension import limiter

from modules.memorias.controllers.memoria_controller import MemoriaController
from modules.shared.services.middleware import requiere_rol


memoria_bp = Blueprint(
    "memoria",
    __name__,
    url_prefix="/memorias"
)


# LECTURA
@memoria_bp.route("", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_all():
    return MemoriaController.get_all()


@memoria_bp.route("/<int:memoria_id>", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_by_id(memoria_id):
    return MemoriaController.get_by_id(memoria_id)


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/investigadores", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_investigadores_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_investigadores_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/becarios", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_becarios_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_becarios_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/personal", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_personal_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_personal_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/proyectos", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_proyectos_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_proyectos_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/actividades-docencia", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_actividades_docencia_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_actividades_docencia_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/participaciones-relevantes", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_participaciones_relevantes_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_participaciones_relevantes_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/documentacion-bibliografica", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_documentacion_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_documentacion_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/equipamiento", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_equipamiento_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_equipamiento_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/erogaciones", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_erogaciones_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_erogaciones_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/transferencias", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_transferencias_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_transferencias_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/trabajos-reunion-cientifica", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_trabajos_reunion_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_trabajos_reunion_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/trabajos-revistas", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_trabajos_revista_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_trabajos_revista_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/distinciones", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_distinciones_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_distinciones_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/registros-propiedad", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_registros_propiedad_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_registros_propiedad_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/articulos-divulgacion", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_articulos_divulgacion_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_articulos_divulgacion_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/visitas-academicas", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_visitas_snapshot(memoria_id, memoria_version_id):
    return MemoriaController.get_visitas_snapshot(
        memoria_id,
        memoria_version_id
    )


@memoria_bp.route("/<int:memoria_id>/versiones/<int:memoria_version_id>/exportar-excel", methods=["GET"])
@limiter.limit(lambda: current_app.config["EXPORT_LIMIT"])
@requiere_rol("ADMIN", "GESTOR")
def exportar_excel(memoria_id, memoria_version_id):
    return MemoriaController.exportar_excel(
        memoria_id,
        memoria_version_id
    )


# MODIFICACION
@memoria_bp.route("", methods=["POST"])
@requiere_rol("ADMIN", "GESTOR")
def create():
    return MemoriaController.create()


@memoria_bp.route("/<int:memoria_id>", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def update(memoria_id):
    return MemoriaController.update(memoria_id)


@memoria_bp.route("/<int:memoria_id>", methods=["DELETE"])
@requiere_rol("ADMIN")
def delete(memoria_id):
    return MemoriaController.delete(memoria_id)


@memoria_bp.route("/<int:memoria_id>/estado", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def change_status(memoria_id):
    return MemoriaController.change_status(memoria_id)


@memoria_bp.route("/<int:memoria_id>/reabrir", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def reopen(memoria_id):
    return MemoriaController.reopen(memoria_id)


@memoria_bp.route("/<int:memoria_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def get_historial(memoria_id):
    return MemoriaController.get_historial(memoria_id)
