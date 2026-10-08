from flask import Blueprint, current_app, request
from extension import limiter
from modules.grupo.controllers.grupo_controller import GrupoUtnController
from modules.shared.services.middleware import requiere_rol

grupo_utn_bp = Blueprint(
    "grupo_utn",
    __name__,
    url_prefix="/grupo-utn"
)

# -------------------------
# Crear grupo UTN
# -------------------------
@grupo_utn_bp.route("/", methods=["POST"], strict_slashes=False)
@requiere_rol("ADMIN", "GESTOR")
def crear():
    return GrupoUtnController.crear()

# -------------------------
# Obtener grupo UTN
# -------------------------
@grupo_utn_bp.route("/", methods=["GET"], strict_slashes=False)
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def obtener():
    return GrupoUtnController.obtener()


@grupo_utn_bp.route("/opciones", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def listar_opciones():
    return GrupoUtnController.listar_opciones()


@grupo_utn_bp.route("/<int:grupo_id>/historial", methods=["GET"])
@requiere_rol("ADMIN", "GESTOR", "LECTURA")
def historial(grupo_id):
    return GrupoUtnController.historial(grupo_id)


# -------------------------
# Actualizar grupo UTN
# -------------------------
@grupo_utn_bp.route("/", methods=["PUT"], strict_slashes=False)
@requiere_rol("ADMIN", "GESTOR")
def actualizar():
    return GrupoUtnController.actualizar()

# -------------------------
# Eliminar grupo UTN
# -------------------------
@grupo_utn_bp.route("/", methods=["DELETE"], strict_slashes=False)
@requiere_rol("ADMIN", "GESTOR")
def eliminar():
    return GrupoUtnController.eliminar()


@grupo_utn_bp.route("/restore", methods=["PUT"])
@requiere_rol("ADMIN", "GESTOR")
def restaurar():
    return GrupoUtnController.restaurar()

@grupo_utn_bp.route("/exportar-excel", methods=["GET"])
@limiter.limit(lambda: current_app.config["EXPORT_LIMIT"])
@requiere_rol("ADMIN", "GESTOR")
def exportar():
    return GrupoUtnController.exportar_excel()
