from flask import Request, Response, g, jsonify

from modules.grupo.models.programa_incentivos import ProgramaIncentivos
from modules.grupo.services.programa_incentivos_service import (
    actualizar_programa_incentivos,
    crear_programa_incentivos,
    eliminar_programa_incentivos,
    listar_programas_incentivos,
    listar_programas_incentivos_paginado,
    obtener_programa_incentivos_por_id,
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class ProgramaIncentivosController:
    @staticmethod
    def crear(req: Request) -> Response:
        try:
            programa = crear_programa_incentivos(req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(programa.serialize()), 201
        except Exception as error:
            return exception_response(error, operation="crear programa de incentivos")

    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                programas, total = listar_programas_incentivos_paginado(**params)
                return paginated_response(
                    [p.serialize() for p in programas], params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            programas = listar_programas_incentivos(req.args.get("activos", "true"))
            return jsonify([p.serialize() for p in programas]), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar programas de incentivos")

    @staticmethod
    def obtener_por_id(req: Request, id: int) -> Response:
        try:
            return jsonify(obtener_programa_incentivos_por_id(id).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar programa de incentivos")

    @staticmethod
    def historial(req: Request, id: int) -> Response:
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(ProgramaIncentivos, id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de programa")

    @staticmethod
    def actualizar(req: Request, id: int) -> Response:
        try:
            programa = actualizar_programa_incentivos(id, req.get_json(), getattr(g, "current_user_id", None))
            return jsonify(programa.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="actualizar programa de incentivos")

    @staticmethod
    def eliminar(req: Request, id: int) -> Response:
        try:
            eliminar_programa_incentivos(id, getattr(g, "current_user_id", None))
            return jsonify({"message": "Programa de incentivos eliminado correctamente"}), 200
        except Exception as error:
            return exception_response(error, operation="eliminar programa de incentivos")
