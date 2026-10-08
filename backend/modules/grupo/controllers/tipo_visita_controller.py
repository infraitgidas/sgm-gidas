from flask import g, jsonify, request

from modules.grupo.models.visita_grupo import TipoVisita
from modules.grupo.services.tipo_visita_service import TipoVisitaService
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class TipoVisitaController:
    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                params = parse_pagination_params(request.args)
                tipos, total = TipoVisitaService.get_page(**params)
                return paginated_response(
                    tipos, params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            return jsonify(TipoVisitaService.get_all(request.args.get("activos", "true"))), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar tipos de visita")

    @staticmethod
    def get_historial(tipo_id):
        try:
            historial = CatalogoAuditoriaService.historial_por_modelo(TipoVisita, tipo_id)
            return jsonify(historial), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de visita")

    @staticmethod
    def create():
        try:
            resultado = TipoVisitaService.create(
                request.get_json(), getattr(g, "current_user_id", None)
            )
            return jsonify(resultado), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de visita")

    @staticmethod
    def update(tipo_id):
        try:
            resultado = TipoVisitaService.update(
                tipo_id, request.get_json(), getattr(g, "current_user_id", None)
            )
            return jsonify(resultado), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de visita")

    @staticmethod
    def delete(tipo_id):
        try:
            resultado = TipoVisitaService.delete(
                tipo_id, getattr(g, "current_user_id", None)
            )
            return jsonify(resultado), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de visita")
