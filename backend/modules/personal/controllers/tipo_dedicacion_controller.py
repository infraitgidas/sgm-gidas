from flask import Request, Response, jsonify, g

from modules.personal.models.personal import TipoDedicacion
from modules.personal.services.tipo_dedicacion_service import (
    actualizar_tipo_dedicacion,
    crear_tipo_dedicacion,
    eliminar_tipo_dedicacion,
    listar_tipos_dedicacion,
    listar_tipos_dedicacion_paginado,
    obtener_tipo_dedicacion_por_id,
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class TipoDedicacionController:

    @staticmethod
    def crear(req: Request) -> Response:
        try:
            tipo = crear_tipo_dedicacion(req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(tipo.serialize()), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de dedicacion")

    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                tipos, total = listar_tipos_dedicacion_paginado(**params)
                return paginated_response(
                    [tipo.serialize() for tipo in tipos], params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            tipos = listar_tipos_dedicacion(req.args.get("activos", "true"))
            return jsonify([tipo.serialize() for tipo in tipos]), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar tipos de dedicacion")

    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            return jsonify(obtener_tipo_dedicacion_por_id(id).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar tipo de dedicacion")

    @staticmethod
    def historial(req: Request, id: int) -> Response:
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(TipoDedicacion, id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de dedicacion")

    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        try:
            tipo = actualizar_tipo_dedicacion(
                id, req.get_json(), getattr(g, "current_user_id", None)
            )
            return jsonify(tipo.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de dedicacion")

    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            tipo = eliminar_tipo_dedicacion(id, getattr(g, "current_user_id", None))
            return jsonify(tipo.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de dedicacion")
