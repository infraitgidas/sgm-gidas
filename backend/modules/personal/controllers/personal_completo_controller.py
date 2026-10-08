from flask import jsonify, request
from modules.personal.services.personal_completo_service import (
    listar_personal_completo,
    listar_personal_paginado,
    obtener_personal_por_tipo
)
from modules.shared.services.logging_config import get_logger
from modules.shared.controllers.responses import exception_response
from modules.shared.exceptions import NotFoundError


logger = get_logger(__name__)


class PersonalCompletoController:

    @staticmethod
    def listar():
        try:
            activos = request.args.get("activos", "true")
            tipo = request.args.get("tipo")
            if "page" not in request.args and "per_page" not in request.args:
                return jsonify(listar_personal_completo(activos, tipo)), 200

            from modules.shared.exceptions import ValidationError

            def entero(nombre, predeterminado):
                try:
                    return int(request.args.get(nombre, predeterminado))
                except (TypeError, ValueError):
                    raise ValidationError(f"El parámetro {nombre} debe ser un entero.")

            ids_param = request.args.get("ids")
            ids = None
            if ids_param is not None:
                try:
                    ids = [int(value) for value in ids_param.split(",") if value.strip()]
                except ValueError:
                    raise ValidationError("Los IDs deben ser enteros positivos.")

            data = listar_personal_paginado(
                activos=activos,
                tipo=tipo,
                page=entero("page", 1),
                per_page=entero("per_page", 9),
                search=request.args.get("search"),
                sort=request.args.get("sort", "fecha_alta"),
                direction=request.args.get("direction", "desc"),
                ids=ids,
            )
            return jsonify(data), 200
        except Exception as error:
            return exception_response(error, operation="listar personal completo")

    @staticmethod
    def obtener_por_id(rol, id):
        try:
            data = obtener_personal_por_tipo(rol, id)

            if not data:
                raise NotFoundError("Personal no encontrado")

            return jsonify(data), 200
        except Exception as error:
            return exception_response(error, operation="consultar personal completo")
