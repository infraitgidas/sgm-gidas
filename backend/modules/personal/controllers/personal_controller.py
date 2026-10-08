from flask import Request, Response, jsonify, g
from modules.personal.services.personal_service import (
    crear_personal,
    actualizar_personal,
    eliminar_personal_por_rol,
    listar_personal,
    listar_personal_pagina,
    obtener_historial_personal_por_rol
)
from modules.personal.services.personal_completo_service import (
    obtener_personal_por_tipo
)
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, exception_response, paginated_response


class PersonalController:

    @staticmethod
    def crear(req: Request) -> Response:
        data = req.get_json(force=True, silent=False)

        try:
            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id  

            personal = crear_personal(data, user_id)

            return jsonify(personal.serialize()), 201

        except Exception as error:
            return exception_response(error, operation="crear personal")


    @staticmethod
    def listar(req: Request) -> Response:
        try:
            if pagination_requested(req.args):
                params = parse_pagination_params(req.args)
                personal, total = listar_personal_pagina(**params)
                return paginated_response(
                    [p.serialize() for p in personal], params["page"],
                    params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            activos = req.args.get("activos")
            personal = listar_personal(activos)
            return jsonify([p.serialize() for p in personal]), 200

        except ValueError as error:
            return error_response("VALIDATION_ERROR", message=str(error), status_code=400)
        except Exception as error:
            return exception_response(error, operation="listar personal")


    @staticmethod
    def obtener_por_id(req: Request, rol: str, id: int) -> Response:
        try:
            personal = obtener_personal_por_tipo(rol, id)

            if not personal:
                return error_response("NOT_FOUND", status_code=404)

            return jsonify(personal), 200

        except Exception as error:
            return exception_response(error, operation="consultar personal")

    @staticmethod
    def obtener_historial(req: Request, rol: str, id: int) -> Response:
        try:
            historial = obtener_historial_personal_por_rol(id, rol)
            return jsonify(historial), 200

        except Exception as error:
            return exception_response(error, operation="consultar historial de personal")


    @staticmethod
    def actualizar(req: Request, rol: str, id: int) -> Response:
        data = req.get_json()

        try:
            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id
            personal = actualizar_personal(id, data, rol, user_id)

            return jsonify(personal.serialize()), 200

        except Exception as error:
            return exception_response(error, operation="actualizar personal")


    @staticmethod
    def eliminar(req, rol, id):
        try:
            if not hasattr(g, "current_user_id"):
                return error_response("AUTH_REQUIRED", status_code=401)

            user_id = g.current_user_id  

            result = eliminar_personal_por_rol(id, rol, user_id)

            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="eliminar personal")
