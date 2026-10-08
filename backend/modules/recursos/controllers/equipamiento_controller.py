from flask import jsonify, request, g
from modules.recursos.services.equipamiento_service import EquipamientoService
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import exception_response, paginated_response
from modules.shared.exceptions import ValidationError


class EquipamientoController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as error:
                    raise ValidationError(str(error)) from error
                data, total = EquipamientoService.get_page(**params)
                return paginated_response(
                    data, params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            activos = request.args.get("activos", "true")
            return jsonify(EquipamientoService.get_all(activos)), 200
        except Exception as error:
            return exception_response(error, operation="listar equipamiento")


    @staticmethod
    def get_by_id(equipamiento_id):
        try:
            return jsonify(
                EquipamientoService.get_by_id(equipamiento_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar equipamiento")

    @staticmethod
    def get_historial(equipamiento_id):
        try:
            return jsonify(
                EquipamientoService.get_historial(equipamiento_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de equipamiento")


    @staticmethod
    def create():
        try:
            data = request.get_json()
            user_id = g.current_user_id

            return jsonify(
                EquipamientoService.create(data, user_id)
            ), 201

        except Exception as error:
            return exception_response(error, operation="crear equipamiento")


    @staticmethod
    def update(equipamiento_id):
        try:
            data = request.get_json()
            user_id = g.current_user_id

            return jsonify(
                EquipamientoService.update(equipamiento_id, data, user_id)
            ), 200

        except Exception as error:
            return exception_response(error, operation="actualizar equipamiento")


    @staticmethod
    def delete(equipamiento_id):
        try:
            user_id = g.current_user_id

            return jsonify(
                EquipamientoService.delete(equipamiento_id, user_id)
            ), 200

        except Exception as error:
            return exception_response(error, operation="eliminar equipamiento")
