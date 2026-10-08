from flask import jsonify, request, g
from modules.grupo.services.directivo_service import DirectivoGrupoService
from modules.shared.controllers.responses import error_response, exception_response
from modules.shared.controllers.responses import paginated_response
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params


def _page_params(args):
    try:
        return parse_pagination_params(args), None
    except ValueError as exc:
        return None, error_response("VALIDATION_ERROR", message=str(exc), status_code=400)


def _page_response(data, total, params):
    return paginated_response(data, params["page"], params["per_page"], total,
                              meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"})


class DirectivoController:

    @staticmethod
    def crear_y_asignar():
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return error_response("VALIDATION_ERROR", status_code=400)
            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)
            return jsonify(DirectivoGrupoService.crear_y_asignar(data, g.current_user_id)), 201
        except Exception as error:
            return exception_response(error, operation="crear y asignar directivo")

    # ==========================================
    # CREAR DIRECTIVO
    # ==========================================
    @staticmethod
    def create():
        try:
            data = request.get_json()

            if not data:
                return error_response("VALIDATION_ERROR", status_code=400)

            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id

            result = DirectivoGrupoService.crear_directivo(data, user_id)

            return jsonify(result), 201

        except Exception as error:
            return exception_response(error, operation="crear directivo")


    # ==========================================
    # GET ALL
    # ==========================================
    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                params, error = _page_params(request.args)
                if error:
                    return error
                data, total = DirectivoGrupoService.get_all_page(params["page"], params["per_page"], params["orden"])
                return _page_response(data, total, params)
            result = DirectivoGrupoService.get_all_srv()
            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="listar directivos")


    # ==========================================
    # UPDATE DIRECTIVO
    # ==========================================
    @staticmethod
    def update(directivo_id):
        try:
            data = request.get_json()

            if not data:
                return error_response("VALIDATION_ERROR", status_code=400)

            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id

            result = DirectivoGrupoService.actualizar_directivo(
                directivo_id,
                data,
                user_id
            )

            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="actualizar directivo")


    # ==========================================
    # ASIGNAR DIRECTIVO A GRUPO
    # ==========================================
    @staticmethod
    def asignar():
        try:
            data = request.get_json()

            if not data:
                return error_response("VALIDATION_ERROR", status_code=400)

            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id

            result = DirectivoGrupoService.asignar_a_grupo(data, user_id)

            return jsonify(result), 201

        except Exception as error:
            return exception_response(error, operation="asignar directivo")


    # ==========================================
    # FINALIZAR CARGO
    # ==========================================
    @staticmethod
    def finalizar():
        try:
            data = request.get_json()

            if not data:
                return error_response("VALIDATION_ERROR", status_code=400)

            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id

            result = DirectivoGrupoService.finalizar_cargo(data, user_id)

            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="finalizar cargo directivo")


    # ==========================================
    # OBTENER DIRECTIVOS POR GRUPO
    # ==========================================
    @staticmethod
    def get_por_grupo(grupo_id):
        try:
            if pagination_requested(request.args):
                params, error = _page_params(request.args)
                if error:
                    return error
                data, total = DirectivoGrupoService.get_por_grupo(grupo_id, params["page"], params["per_page"])
                return _page_response(data, total, params)
            result = DirectivoGrupoService.get_por_grupo(grupo_id)
            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="consultar directivos por grupo")


    @staticmethod
    def get_actuales(grupo_id):
        try:
            if pagination_requested(request.args):
                params, error = _page_params(request.args)
                if error:
                    return error
                data, total = DirectivoGrupoService.get_actuales_por_grupo(grupo_id, params["page"], params["per_page"])
                return _page_response(data, total, params)
            result = DirectivoGrupoService.get_actuales_por_grupo(grupo_id)
            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="consultar directivos actuales")

    @staticmethod
    def get_cambios(grupo_id):
        try:
            try:
                page = int(request.args.get("page", "1"))
            except (TypeError, ValueError):
                return error_response("VALIDATION_ERROR", status_code=400)
            if page < 1:
                return error_response("VALIDATION_ERROR", status_code=400)
            return jsonify(DirectivoGrupoService.get_cambios_por_grupo(grupo_id, page)), 200
        except Exception as error:
            return exception_response(error, operation="consultar cambios de directivos")
