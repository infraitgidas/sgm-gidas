from flask import jsonify, request, g
from modules.produccion.services.distincion_service import DistincionRecibidaService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, filtered_page_response


class DistincionRecibidaController:

    @staticmethod
    def get_all():
        try:
            filtros = {
                "proyecto_id": request.args.get("proyecto_id", type=int),
                "orden": request.args.get("orden"),
                "activos": request.args.get("activos", "true")
            }

            if pagination_requested(request.args):
                return filtered_page_response(DistincionRecibidaService, filtros, request.args)
            return jsonify(
                DistincionRecibidaService.get_all(filtros)
            ), 200

        except Exception as error:
            return exception_response(error, operation="listar distinciones")

    @staticmethod
    def get_by_id(distincion_id):
        try:
            return jsonify(
                DistincionRecibidaService.get_by_id(distincion_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar distincion")

    @staticmethod
    def get_historial(distincion_id):
        try:
            return jsonify(
                DistincionRecibidaService.get_historial(distincion_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de distincion")

    @staticmethod
    def create():
        try:
            data = request.get_json()
            user_id = g.current_user_id
            return jsonify(
                DistincionRecibidaService.create(data, user_id)
            ), 201
        except Exception as error:
            return exception_response(error, operation="crear distincion")

    @staticmethod
    def update(distincion_id):
        try:
            data = request.get_json()
            user_id = g.current_user_id
            return jsonify(
                DistincionRecibidaService.update(distincion_id, data, user_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="actualizar distincion")

    @staticmethod
    def delete(distincion_id):
        try:
            user_id = g.current_user_id
            return jsonify(
                DistincionRecibidaService.delete(distincion_id, user_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar distincion")
