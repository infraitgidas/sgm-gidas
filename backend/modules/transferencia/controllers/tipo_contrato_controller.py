from flask import g, jsonify, request

from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import exception_response, paginated_response
from modules.shared.exceptions import ValidationError
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.transferencia.models.transferencia_socio import TipoContrato
from modules.transferencia.services.tipo_contrato_service import TipoContratoService


class TipoContratoController:
    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as error:
                    raise ValidationError(str(error)) from error
                data, total = TipoContratoService.get_page(**params)
                return paginated_response(
                    data, params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            return jsonify(TipoContratoService.get_all(request.args.get("activos", "true"))), 200
        except Exception as error:
            return exception_response(error, operation="listar tipos de contrato")

    @staticmethod
    def get_by_id(tipo_contrato_id):
        try:
            return jsonify(TipoContratoService.get_by_id(tipo_contrato_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar tipo de contrato")

    @staticmethod
    def get_historial(tipo_contrato_id):
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(TipoContrato, tipo_contrato_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de contrato")

    @staticmethod
    def create():
        try:
            return jsonify(TipoContratoService.create(request.get_json(), getattr(g, "current_user_id", None))), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de contrato")

    @staticmethod
    def update(tipo_contrato_id):
        try:
            return jsonify(TipoContratoService.update(tipo_contrato_id, request.get_json(), getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de contrato")

    @staticmethod
    def delete(tipo_contrato_id):
        try:
            return jsonify(TipoContratoService.delete(tipo_contrato_id, getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de contrato")
