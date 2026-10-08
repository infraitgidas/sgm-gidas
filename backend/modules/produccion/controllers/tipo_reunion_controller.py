from flask import g, jsonify, request

from modules.produccion.models.trabajo_reunion import TipoReunion
from modules.produccion.services.tipo_reunion_service import TipoReunionService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class TipoReunionController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(TipoReunionService, request.args)
            return jsonify(TipoReunionService.get_all(request.args.get("activos", "true"))), 200
        except Exception as error:
            return exception_response(error, operation="listar tipos de reunion")

    @staticmethod
    def get_historial(tipo_id):
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(TipoReunion, tipo_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de reunion")

    @staticmethod
    def create():
        try:
            return jsonify(TipoReunionService.create(request.get_json(), getattr(g, "current_user_id", None))), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de reunion")

    @staticmethod
    def update(tipo_id):
        try:
            return jsonify(TipoReunionService.update(tipo_id, request.get_json(), getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de reunion")

    @staticmethod
    def delete(tipo_id):
        try:
            return jsonify(TipoReunionService.delete(tipo_id, getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de reunion")
