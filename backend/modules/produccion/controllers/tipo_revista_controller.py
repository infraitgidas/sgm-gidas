from flask import g, jsonify, request

from modules.produccion.models.trabajo_revista import TipoRevista
from modules.produccion.services.tipo_revista_service import TipoRevistaService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class TipoRevistaController:
    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(TipoRevistaService, request.args)
            return jsonify(TipoRevistaService.get_all(request.args.get("activos", "true"))), 200
        except Exception as error:
            return exception_response(error, operation="listar tipos de revista")

    @staticmethod
    def get_historial(tipo_id):
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(TipoRevista, tipo_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de revista")

    @staticmethod
    def create():
        try:
            return jsonify(TipoRevistaService.create(request.get_json(), getattr(g, "current_user_id", None))), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de revista")

    @staticmethod
    def update(tipo_id):
        try:
            return jsonify(TipoRevistaService.update(tipo_id, request.get_json(), getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de revista")

    @staticmethod
    def delete(tipo_id):
        try:
            return jsonify(TipoRevistaService.delete(tipo_id, getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de revista")
