from flask import g, jsonify, request

from modules.informes.services.informe_service import InformeService
from modules.shared.controllers.responses import exception_response, paginated_response
from modules.shared.exceptions import ValidationError


class InformeController:
    @staticmethod
    def candidates(tipo):
        try:
            memoria_id = InformeController._integer(request.args.get("memoria_id"), None)
            page = InformeController._integer(request.args.get("page"), 1)
            per_page = InformeController._integer(request.args.get("per_page"), 9)
            data, total = InformeService.candidates(tipo, memoria_id, request.args.get("search", ""), page, per_page)
            return paginated_response(data, page, per_page, total)
        except Exception as error:
            return exception_response(error, operation="buscar registros para informe")

    @staticmethod
    def _integer(value, default):
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError) as error:
            raise ValidationError("Revise los filtros indicados.") from error

    @staticmethod
    def list(tipo):
        try:
            page = InformeController._integer(request.args.get("page"), 1)
            per_page = InformeController._integer(request.args.get("per_page"), 9)
            memoria_id = request.args.get("memoria_id")
            memoria_id = InformeController._integer(memoria_id, None) if memoria_id else None
            data, total = InformeService.list(tipo, memoria_id, page, per_page)
            return paginated_response(data, page, per_page, total)
        except Exception as error:
            return exception_response(error, operation="listar informes")

    @staticmethod
    def get(tipo, informe_id):
        try:
            return jsonify(InformeService.get(tipo, informe_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar informe")

    @staticmethod
    def create(tipo):
        try:
            return jsonify(InformeService.create(tipo, request.get_json(silent=True), g.current_user_id)), 201
        except Exception as error:
            return exception_response(error, operation="crear informe")

    @staticmethod
    def update(tipo, informe_id):
        try:
            return jsonify(InformeService.update(tipo, informe_id, request.get_json(silent=True), g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="actualizar informe")

    @staticmethod
    def delete(tipo, informe_id):
        try:
            return jsonify(InformeService.delete(tipo, informe_id, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="eliminar informe")

    @staticmethod
    def history(tipo, informe_id):
        try:
            return jsonify(InformeService.history(tipo, informe_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de informe")
