from flask import jsonify, request, g, send_file

from modules.memorias.services.memoria_service import MemoriaService
from modules.memorias.services.exportacion_service_impl import ExportService
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response


class MemoriaController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                params = parse_pagination_params(request.args)
                memorias, total = MemoriaService.get_page(**params)
                return paginated_response(
                    memorias, params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            activos = request.args.get("activos", "true")
            return jsonify(MemoriaService.get_all(activos)), 200
        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar memorias")

    @staticmethod
    def get_by_id(memoria_id):
        try:
            return jsonify(
                MemoriaService.get_by_id(memoria_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar memoria")

    @staticmethod
    def get_investigadores_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_investigadores_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_becarios_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_becarios_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_personal_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_personal_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_proyectos_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_proyectos_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_actividades_docencia_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_actividades_docencia_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_participaciones_relevantes_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_participaciones_relevantes_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_documentacion_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_documentacion_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_equipamiento_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_equipamiento_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_erogaciones_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_erogaciones_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_transferencias_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_transferencias_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_trabajos_reunion_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_trabajos_reunion_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_trabajos_revista_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_trabajos_revista_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_distinciones_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_distinciones_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_registros_propiedad_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_registros_propiedad_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_articulos_divulgacion_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_articulos_divulgacion_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def get_visitas_snapshot(memoria_id, memoria_version_id):
        try:
            return jsonify(
                MemoriaService.get_visitas_snapshot(
                    memoria_id,
                    memoria_version_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar snapshot de memoria")

    @staticmethod
    def exportar_excel(memoria_id, memoria_version_id):
        try:
            archivo = ExportService.generar_excel_memoria(
                memoria_id,
                memoria_version_id
            )
            memoria = MemoriaService.get_by_id(memoria_id)
            versiones = memoria.get("versiones", [])
            version = next(
                (item for item in versiones if item.get("id") == memoria_version_id),
                None
            )
            periodo = f"{memoria['periodo_inicio']}_{memoria['periodo_fin']}"
            numero_version = (
                version.get("numero_version")
                if version and version.get("numero_version") is not None
                else memoria_version_id
            )

            return send_file(
                archivo,
                as_attachment=True,
                download_name=f"memoria_{periodo}_v{numero_version}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as error:
            return exception_response(error, operation="exportar memoria")

    @staticmethod
    def create():
        try:
            data = request.get_json()
            user_id = g.current_user_id

            return jsonify(
                MemoriaService.create(data, user_id)
            ), 201
        except Exception as error:
            return exception_response(error, operation="crear memoria")

    @staticmethod
    def update(memoria_id):
        try:
            data = request.get_json()

            return jsonify(
                MemoriaService.update(memoria_id, data, g.current_user_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="actualizar memoria")

    @staticmethod
    def delete(memoria_id):
        try:
            user_id = g.current_user_id

            return jsonify(
                MemoriaService.delete(memoria_id, user_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar memoria")

    @staticmethod
    def change_status(memoria_id):
        try:
            data = request.get_json()
            user_id = g.current_user_id

            return jsonify(
                MemoriaService.change_status(memoria_id, data, user_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="cambiar estado de memoria")

    @staticmethod
    def reopen(memoria_id):
        try:
            data = request.get_json(silent=True) or {}
            user_id = g.current_user_id

            return jsonify(
                MemoriaService.reopen(memoria_id, user_id, data)
            ), 200
        except Exception as error:
            return exception_response(error, operation="reabrir memoria")

    @staticmethod
    def get_historial(memoria_id):
        try:
            return jsonify(MemoriaService.get_historial(memoria_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de memoria")
