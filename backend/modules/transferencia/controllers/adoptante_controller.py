from flask import g, jsonify, request

from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import exception_response, paginated_response
from modules.shared.exceptions import ValidationError
from modules.transferencia.services.adoptante_service import AdoptanteService


class AdoptanteController:
    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as error:
                    raise ValidationError(str(error)) from error
                data, total = AdoptanteService.get_page(**params)
                return paginated_response(
                    data, params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            return jsonify(AdoptanteService.get_all(request.args.get("activos", "true"))), 200
        except Exception as error:
            return exception_response(error, operation="listar adoptantes")

    @staticmethod
    def get_by_id(adoptante_id):
        try:
            return jsonify(AdoptanteService.get_by_id(adoptante_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar adoptante")

    @staticmethod
    def get_historial(adoptante_id):
        try:
            return jsonify(AdoptanteService.get_historial(adoptante_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de adoptante")

    @staticmethod
    def create():
        try:
            data = request.get_json()
            if not data:
                raise ValidationError("Body requerido")
            return jsonify(AdoptanteService.create(data, g.current_user_id)), 201
        except Exception as error:
            return exception_response(error, operation="crear adoptante")

    @staticmethod
    def update(adoptante_id):
        try:
            data = request.get_json()
            if not data:
                raise ValidationError("Body requerido")
            return jsonify(AdoptanteService.update(adoptante_id, data, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="actualizar adoptante")

    @staticmethod
    def delete(adoptante_id):
        try:
            return jsonify(AdoptanteService.delete(adoptante_id, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="eliminar adoptante")
