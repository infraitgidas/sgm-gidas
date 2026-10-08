from flask import Request, Response, jsonify, g
from modules.personal.services.investigador_service import (
    crear_investigador,
    actualizar_investigador,
    eliminar_investigador,
    restaurar_investigador,
    listar_investigadores,
    listar_investigadores_paginado,
    obtener_investigador_por_id,
    obtener_historial_investigador
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response


class InvestigadorController:

    # =====================================================
    # CREATE
    # =====================================================
    @staticmethod
    def crear(req: Request) -> Response:
        try:
            data = req.get_json()

            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id

            investigador = crear_investigador(data, user_id)

            return jsonify(investigador.serialize()), 201

        except Exception as error:
            return exception_response(error, operation="crear investigador")


    # =====================================================
    # LISTAR
    # =====================================================
    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                investigadores, total = listar_investigadores_paginado(**params)
                return paginated_response(
                    [i.serialize() for i in investigadores],
                    params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            activos = req.args.get("activos")
            investigadores = listar_investigadores(activos)

            return jsonify([i.serialize() for i in investigadores]), 200

        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar investigadores")


    # =====================================================
    # OBTENER POR ID
    # =====================================================
    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            investigador = obtener_investigador_por_id(id)

            return jsonify(investigador.serialize()), 200

        except Exception as error:
            return exception_response(error, operation="consultar investigador")

    @staticmethod
    def obtener_historial(req: Request, id: int) -> Response:
        try:
            historial = obtener_historial_investigador(id)
            return jsonify(historial), 200

        except Exception as error:
            return exception_response(error, operation="consultar historial de investigador")


    # =====================================================
    # UPDATE
    # =====================================================
    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        try:
            data = req.get_json()

            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id

            investigador = actualizar_investigador(id, data, user_id)

            return jsonify(investigador.serialize()), 200

        except Exception as error:
            return exception_response(error, operation="actualizar investigador")


    # =====================================================
    # DELETE
    # =====================================================
    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id

            result = eliminar_investigador(id, user_id)

            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="eliminar investigador")


    # =====================================================
    # RESTAURAR
    # =====================================================
    @staticmethod
    def restaurar(req: Request, id: int) -> Response:
        try:
            investigador = restaurar_investigador(id)

            return jsonify(investigador.serialize()), 200

        except Exception as error:
            return exception_response(error, operation="restaurar investigador")
