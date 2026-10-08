from flask import Request, Response, g, jsonify

from modules.catalogos.models.categoria_utn import CategoriaUtn
from modules.catalogos.services.categoria_utn_service import (
    actualizar_categoria_utn, crear_categoria_utn, eliminar_categoria_utn,
    listar_categorias_utn, listar_categorias_utn_paginado, obtener_categoria_utn_por_id,
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class CategoriaUtnController:
    @staticmethod
    def crear(req: Request) -> Response:
        try:
            categoria = crear_categoria_utn(req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(categoria.serialize()), 201
        except Exception as error:
            return exception_response(error, operation="crear categoria UTN")

    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                categorias, total = listar_categorias_utn_paginado(**params)
                return paginated_response(
                    [c.serialize() for c in categorias], params["page"],
                    params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            return jsonify([c.serialize() for c in listar_categorias_utn(req.args.get("activos", "true"))]), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar categorias UTN")

    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            return jsonify(obtener_categoria_utn_por_id(id).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar categoria UTN")

    @staticmethod
    def historial(req: Request, id: int) -> Response:
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(CategoriaUtn, id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de categoria UTN")

    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        try:
            categoria = actualizar_categoria_utn(id, req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(categoria.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="actualizar categoria UTN")

    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            eliminar_categoria_utn(id, getattr(g, "current_user_id", None))
            return jsonify({"message": "Categoría UTN eliminada correctamente"}), 200
        except Exception as error:
            return exception_response(error, operation="eliminar categoria UTN")
