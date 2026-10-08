from flask import jsonify, request, g
from modules.recursos.services.tipo_erogacion_service import TipoErogacionService
from modules.recursos.models.erogacion import TipoErogacion
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response

class TipoErogacionController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(TipoErogacionService, request.args)
            return jsonify(
                TipoErogacionService.get_all(request.args.get("activos", "true"))
            ), 200
        except Exception as error:
            return exception_response(error, operation="listar tipos de erogacion")

    @staticmethod
    def get_by_id(tipo_id):
        try:
            return jsonify(
                TipoErogacionService.get_by_id(tipo_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar tipo de erogacion")

    @staticmethod
    def get_historial(tipo_id):
        try:
            return jsonify(
                CatalogoAuditoriaService.historial_por_modelo(TipoErogacion, tipo_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de erogacion")

    @staticmethod
    def create():
        try:
            data = request.get_json()
            return jsonify(
                TipoErogacionService.create(data, getattr(g, "current_user_id", None))
            ), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de erogacion")

    @staticmethod
    def update(tipo_id):
        try:
            data = request.get_json()
            return jsonify(
                TipoErogacionService.update(
                    tipo_id,
                    data,
                    getattr(g, "current_user_id", None)
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de erogacion")

    @staticmethod
    def delete(tipo_id):
        try:
            return jsonify(
                TipoErogacionService.delete(tipo_id, getattr(g, "current_user_id", None))
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de erogacion")
