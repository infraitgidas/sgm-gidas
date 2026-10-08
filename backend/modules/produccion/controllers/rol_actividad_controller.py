from flask import g, jsonify, request

from modules.produccion.models.actividad_docencia import RolActividad
from modules.produccion.services.rol_actividad_service import RolActividadService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class RolActividadController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(RolActividadService, request.args)
            return jsonify(
                RolActividadService.get_all(request.args.get("activos", "true"))
            ), 200
        except Exception as error:
            return exception_response(error, operation="listar roles de actividad")

    @staticmethod
    def get_by_id(rol_id):
        try:
            return jsonify(RolActividadService.get_by_id(rol_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar rol de actividad")

    @staticmethod
    def get_historial(rol_id):
        try:
            return jsonify(
                CatalogoAuditoriaService.historial_por_modelo(RolActividad, rol_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de rol de actividad")

    @staticmethod
    def create():
        try:
            return jsonify(
                RolActividadService.create(
                    request.get_json(),
                    getattr(g, "current_user_id", None),
                )
            ), 201
        except Exception as error:
            return exception_response(error, operation="crear rol de actividad")

    @staticmethod
    def update(rol_id):
        try:
            return jsonify(
                RolActividadService.update(
                    rol_id,
                    request.get_json(),
                    getattr(g, "current_user_id", None),
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="actualizar rol de actividad")

    @staticmethod
    def delete(rol_id):
        try:
            return jsonify(
                RolActividadService.delete(
                    rol_id,
                    getattr(g, "current_user_id", None),
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar rol de actividad")
