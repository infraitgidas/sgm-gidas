from flask import Request, Response, jsonify, g
from modules.grupo.services.visita_service import (
    crear_visita_academica,
    actualizar_visita_academica,
    eliminar_visita_academica,
    listar_visitas,
    listar_visitas_paginado,
    obtener_visita_por_id,
    obtener_historial_visita,
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response


class VisitaAcademicaController:

    @staticmethod
    def crear(req: Request) -> Response:
        data = req.get_json()
        try:
            visita = crear_visita_academica(data, g.current_user_id)
            return jsonify(visita.serialize()), 201
        except Exception as error:
            return exception_response(error, operation="crear visita academica")

    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                visitas, total = listar_visitas_paginado(**params)
                return paginated_response(
                    [v.serialize() for v in visitas], params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            activos = req.args.get("activos", "true")
            visitas = listar_visitas(activos)
            return jsonify([v.serialize() for v in visitas]), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar visitas academicas")

    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            visita = obtener_visita_por_id(id)
            return jsonify(visita.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar visita academica")

    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        data = req.get_json()
        try:
            data["user_id"] = g.current_user_id
            visita = actualizar_visita_academica(id, data)
            return jsonify(visita.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="actualizar visita academica")

    @staticmethod
    def obtener_historial(req: Request, id: int) -> Response:
        try:
            historial = obtener_historial_visita(id)
            return jsonify(historial), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de visita")

    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            eliminar_visita_academica(id, g.current_user_id)
            return jsonify(
                {"message": "Visita academica eliminada correctamente"}
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar visita academica")
