from flask import g, jsonify, request

from modules.produccion.services.registro_propiedad_service import RegistrosPropiedadService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, paginated_response


class RegistrosPropiedadController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as exc:
                    return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
                data, total = RegistrosPropiedadService.get_page(
                    params["activos"], params["page"], params["per_page"], params["orden"]
                )
                return paginated_response(data, params["page"], params["per_page"], total,
                                          meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"})
            return jsonify(RegistrosPropiedadService.get_all(request.args.get("activos", "true"))), 200
        except Exception as error:
            return exception_response(error, operation="listar registros de propiedad")

    @staticmethod
    def get_by_id(registro_id):
        try:
            return jsonify(RegistrosPropiedadService.get_by_id(registro_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar registro de propiedad")

    @staticmethod
    def get_historial(registro_id):
        try:
            return jsonify(RegistrosPropiedadService.get_historial(registro_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de registro")

    @staticmethod
    def create():
        try:
            return jsonify(RegistrosPropiedadService.create(request.get_json(), g.current_user_id)), 201
        except Exception as error:
            return exception_response(error, operation="crear registro de propiedad")

    @staticmethod
    def update(registro_id):
        try:
            return jsonify(RegistrosPropiedadService.update(registro_id, request.get_json(), g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="actualizar registro de propiedad")

    @staticmethod
    def delete(registro_id):
        try:
            return jsonify(RegistrosPropiedadService.delete(registro_id, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="eliminar registro de propiedad")

    @staticmethod
    def restore(registro_id):
        try:
            return jsonify(RegistrosPropiedadService.restore(registro_id)), 200
        except Exception as error:
            return exception_response(error, operation="restaurar registro de propiedad")
