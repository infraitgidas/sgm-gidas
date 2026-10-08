from flask import Request, Response, jsonify, g

from modules.personal.models.tipo_personal import TipoPersonal
from modules.personal.services.tipo_personal_service import (
    actualizar_tipo_personal,
    crear_tipo_personal,
    eliminar_tipo_personal,
    listar_tipos,
    listar_tipos_paginado,
    obtener_tipo_por_id,
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class TipoPersonalController:

    @staticmethod
    def crear(req: Request) -> Response:
        try:
            tipo = crear_tipo_personal(req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(tipo.serialize()), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de personal")

    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                tipos, total = listar_tipos_paginado(**params)
                return paginated_response(
                    [tipo.serialize() for tipo in tipos], params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            tipos = listar_tipos(req.args.get("activos", "true"))
            return jsonify([tipo.serialize() for tipo in tipos]), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar tipos de personal")

    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            return jsonify(obtener_tipo_por_id(id).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar tipo de personal")

    @staticmethod
    def historial(req: Request, id: int) -> Response:
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(TipoPersonal, id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de personal")

    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        try:
            tipo = actualizar_tipo_personal(
                id, req.get_json(), getattr(g, "current_user_id", None)
            )
            return jsonify(tipo.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de personal")

    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            tipo = eliminar_tipo_personal(id, getattr(g, "current_user_id", None))
            return jsonify(tipo.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de personal")
