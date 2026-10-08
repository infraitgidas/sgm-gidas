from flask import Request, Response, jsonify, g

from modules.personal.services.becario_service import (
    actualizar_becario,
    crear_becario,
    eliminar_becario,
    listar_becarios,
    listar_becarios_paginado,
    obtener_becario_por_id,
    obtener_historial_becario,
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response


class BecarioController:

    @staticmethod
    def crear(req: Request) -> Response:
        try:
            becario = crear_becario(req.get_json(), g.current_user_id)
            return jsonify(becario.serialize()), 201
        except Exception as error:
            return exception_response(error, operation="crear becario")

    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                becarios, total = listar_becarios_paginado(**params)
                return paginated_response(
                    [becario.serialize() for becario in becarios],
                    params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            becarios = listar_becarios(req.args.get("activos"))
            return jsonify([becario.serialize() for becario in becarios]), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar becarios")

    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            return jsonify(obtener_becario_por_id(id).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar becario")

    @staticmethod
    def obtener_historial(req: Request, id: int) -> Response:
        try:
            return jsonify(obtener_historial_becario(id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de becario")

    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        try:
            becario = actualizar_becario(id, req.get_json(), g.current_user_id)
            return jsonify(becario.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="actualizar becario")

    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            return jsonify(eliminar_becario(id, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="eliminar becario")
