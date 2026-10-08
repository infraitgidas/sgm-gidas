from flask import Request, Response, g, jsonify

from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.catalogos.services.fuente_financiamiento_service import (
    actualizar_fuente_financiamiento, crear_fuente_financiamiento,
    eliminar_fuente_financiamiento, listar_fuentes_financiamiento, listar_fuentes_financiamiento_paginado,
    obtener_fuente_financiamiento_por_id,
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class FuenteFinanciamientoController:
    @staticmethod
    def crear(req: Request) -> Response:
        try:
            fuente = crear_fuente_financiamiento(req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(fuente.serialize()), 201
        except Exception as error:
            return exception_response(error, operation="crear fuente de financiamiento")

    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                fuentes, total = listar_fuentes_financiamiento_paginado(**params)
                return paginated_response(
                    [f.serialize() for f in fuentes], params["page"],
                    params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            return jsonify([f.serialize() for f in listar_fuentes_financiamiento(req.args.get("activos", "true"))]), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar fuentes de financiamiento")

    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            return jsonify(obtener_fuente_financiamiento_por_id(id).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar fuente de financiamiento")

    @staticmethod
    def historial(req: Request, id: int) -> Response:
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(FuenteFinanciamiento, id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de fuente")

    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        try:
            fuente = actualizar_fuente_financiamiento(id, req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(fuente.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="actualizar fuente de financiamiento")

    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            fuente = eliminar_fuente_financiamiento(id, getattr(g, "current_user_id", None))
            return jsonify(fuente.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="eliminar fuente de financiamiento")
