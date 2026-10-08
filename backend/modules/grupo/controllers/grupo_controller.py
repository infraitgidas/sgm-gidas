from flask import jsonify, request, g, send_file
from modules.grupo.services.grupo_service import (
    crear_grupo_utn,
    obtener_grupo_utn,
    actualizar_grupo_utn,
    eliminar_grupo_utn,
    restaurar_grupo_utn,
    listar_grupos_utn_activos,
    obtener_historial_grupo_utn,
)
from modules.memorias.services.exportacion_service_impl import ExportService
from modules.shared.controllers.responses import error_response, exception_response
from modules.shared.controllers.responses import paginated_response
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.services.logging_config import get_logger


logger = get_logger(__name__)

class GrupoUtnController:

    @staticmethod
    def listar_opciones():
        try:
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as exc:
                    return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
                data, total = listar_grupos_utn_activos(params["page"], params["per_page"], params["orden"])
                return paginated_response(data, params["page"], params["per_page"], total,
                                          meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"})
            return jsonify(listar_grupos_utn_activos()), 200
        except Exception as error:
            return exception_response(error, operation="listar grupos UTN")

    @staticmethod
    def crear():
        try:
            data = request.get_json()
            user_id = g.current_user_id

            grupo = crear_grupo_utn(data, user_id)

            return jsonify(grupo.serialize()), 201

        except Exception as error:
            return exception_response(error, operation="crear grupo UTN")


    @staticmethod
    def obtener():
        try:
            grupo = obtener_grupo_utn()

            if not grupo:
                return error_response("NOT_FOUND", status_code=404)

            return jsonify(grupo.serialize()), 200

        except Exception as error:
            return exception_response(error, operation="consultar grupo UTN")


    @staticmethod
    def actualizar():
        try:
            data = request.get_json()
            grupo = actualizar_grupo_utn(data, g.current_user_id)

            return jsonify(grupo.serialize()), 200

        except Exception as error:
            return exception_response(error, operation="actualizar grupo UTN")

    @staticmethod
    def historial(grupo_id):
        try:
            return jsonify(obtener_historial_grupo_utn(grupo_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de grupo UTN")


    @staticmethod
    def eliminar():
        try:
            user_id = g.current_user_id

            result = eliminar_grupo_utn(user_id)

            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="eliminar grupo UTN")
        
    @staticmethod
    def restaurar():
        try:
            grupo = restaurar_grupo_utn()
            return jsonify(grupo.serialize()), 200
        except Exception as error:
            return exception_response(error, operation="restaurar grupo UTN")
            
            
    @staticmethod
    def exportar_excel():
        try:
            grupo = obtener_grupo_utn()
            if not grupo:
                return error_response("NOT_FOUND", status_code=404)

            archivo = ExportService.generar_excel_grupo(grupo.id)

            return send_file(
                archivo,
                as_attachment=True,
                download_name="reporte_GIDAS.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ValueError:
            logger.exception("Error de validacion al exportar grupo UTN")
            return error_response("VALIDATION_ERROR", status_code=400)
        except Exception:
            logger.exception("Error interno al exportar grupo UTN")
            return error_response("INTERNAL_ERROR", status_code=500)
