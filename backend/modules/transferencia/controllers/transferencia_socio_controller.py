from flask import g, jsonify, request

from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params, table_page_response
from modules.shared.controllers.responses import exception_response, paginated_response
from modules.shared.exceptions import ValidationError
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService


class TransferenciaSocioProductivaController:
    @staticmethod
    def get_all():
        try:
            filtros = {
                "grupo_utn_id": request.args.get("grupo_utn_id", type=int),
                "tipo_contrato_id": request.args.get("tipo_contrato_id", type=int),
                "activos": request.args.get("activos", "true"),
            }
            if request.args.get("view") == "table":
                return table_page_response(TransferenciaSocioProductivaService, filtros, request.args)
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as error:
                    raise ValidationError(str(error)) from error
                data, total = TransferenciaSocioProductivaService.get_page(
                    filtros, params["page"], params["per_page"], params["orden"]
                )
                return paginated_response(
                    data, params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            return jsonify(TransferenciaSocioProductivaService.get_all(filtros)), 200
        except Exception as error:
            return exception_response(error, operation="listar transferencias")

    @staticmethod
    def get_by_id(transferencia_id):
        try:
            return jsonify(TransferenciaSocioProductivaService.get_by_id(transferencia_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar transferencia")

    @staticmethod
    def get_historial(transferencia_id):
        try:
            return jsonify(TransferenciaSocioProductivaService.get_historial(transferencia_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de transferencia")

    @staticmethod
    def create():
        try:
            data = request.get_json()
            if not data:
                raise ValidationError("Body requerido")
            return jsonify(TransferenciaSocioProductivaService.create(data, g.current_user_id)), 201
        except Exception as error:
            return exception_response(error, operation="crear transferencia")

    @staticmethod
    def update(transferencia_id):
        try:
            data = request.get_json()
            if not data:
                raise ValidationError("Body requerido")
            return jsonify(TransferenciaSocioProductivaService.update(transferencia_id, data, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="actualizar transferencia")

    @staticmethod
    def delete(transferencia_id):
        try:
            return jsonify(TransferenciaSocioProductivaService.delete(transferencia_id, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="eliminar transferencia")

    @staticmethod
    def restore(transferencia_id):
        try:
            return jsonify(TransferenciaSocioProductivaService.restore(transferencia_id)), 200
        except Exception as error:
            return exception_response(error, operation="restaurar transferencia")

    @staticmethod
    def _adoptantes_ids():
        data = request.get_json()
        if not data:
            raise ValidationError("Body requerido")
        adoptantes_ids = data.get("adoptantes_ids")
        if not isinstance(adoptantes_ids, list) or not adoptantes_ids:
            raise ValidationError("adoptantes_ids debe ser una lista no vacía")
        return adoptantes_ids

    @staticmethod
    def add_adoptantes(transferencia_id):
        try:
            return jsonify(TransferenciaSocioProductivaService.add_adoptantes(transferencia_id, TransferenciaSocioProductivaController._adoptantes_ids(), g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="vincular adoptantes")

    @staticmethod
    def remove_adoptantes(transferencia_id):
        try:
            return jsonify(TransferenciaSocioProductivaService.remove_adoptantes(transferencia_id, TransferenciaSocioProductivaController._adoptantes_ids(), g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="desvincular adoptantes")
