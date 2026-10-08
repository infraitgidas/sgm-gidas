from flask import g, jsonify, request
from modules.produccion.services.articulo_divulgacion_service import ArticuloDivulgacionService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, filtered_page_response


class ArticuloDivulgacionController:

    @staticmethod
    def crear():
        try:
            data = request.get_json()
            user_id = g.current_user_id

            articulo = ArticuloDivulgacionService.create(data, user_id)
            return jsonify(articulo), 201

        except Exception as error:
            return exception_response(error, operation="crear articulo de divulgacion")

    @staticmethod
    def listar():
        try:
            filters = {
                "grupo_utn_id": request.args.get("grupo_utn_id", type=int),
                "orden": request.args.get("orden"),
                "activos": request.args.get("activos", "true")
            }

            if pagination_requested(request.args):
                return filtered_page_response(ArticuloDivulgacionService, filters, request.args)
            articulos = ArticuloDivulgacionService.get_all(filters)
            return jsonify(articulos), 200

        except Exception as error:
            return exception_response(error, operation="listar articulos de divulgacion")

    @staticmethod
    def obtener_por_id(articulo_id: int):
        try:
            articulo = ArticuloDivulgacionService.get_by_id(articulo_id)
            return jsonify(articulo), 200

        except Exception as error:
            return exception_response(error, operation="consultar articulo de divulgacion")

    @staticmethod
    def obtener_historial(articulo_id: int):
        try:
            historial = ArticuloDivulgacionService.get_historial(articulo_id)
            return jsonify(historial), 200

        except Exception as error:
            return exception_response(error, operation="consultar historial de articulo")

    @staticmethod
    def actualizar(articulo_id: int):
        try:
            data = request.get_json()
            articulo = ArticuloDivulgacionService.update(
                articulo_id,
                data,
                user_id=g.current_user_id
            )
            return jsonify(articulo), 200

        except Exception as error:
            return exception_response(error, operation="actualizar articulo de divulgacion")

    @staticmethod
    def eliminar(articulo_id: int):
        try:
            result = ArticuloDivulgacionService.delete(
                articulo_id,
                g.current_user_id
            )
            return jsonify(result), 200

        except Exception as error:
            return exception_response(error, operation="eliminar articulo de divulgacion")
