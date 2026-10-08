from flask import jsonify, request, g
from modules.produccion.services.autores_service import AutorService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response

class AutorController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(AutorService, request.args)
            return jsonify(AutorService.get_all(request.args.get("activos", "true"))), 200
        except Exception as error:
            return exception_response(error, operation="listar autores")

    @staticmethod
    def get_by_id(autor_id):
        try:
            return jsonify(
                AutorService.get_by_id(autor_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar autor")

    @staticmethod
    def get_historial(autor_id):
        try:
            return jsonify(AutorService.get_historial(autor_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de autor")

    @staticmethod
    def create():
        try:
            data = request.get_json()
            return jsonify(
                AutorService.create(data, g.current_user_id)
            ), 201
        except Exception as error:
            return exception_response(error, operation="crear autor")

    @staticmethod
    def update(autor_id):
        try:
            data = request.get_json()
            return jsonify(
                AutorService.update(autor_id, data, g.current_user_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="actualizar autor")

    @staticmethod
    def delete(autor_id):
        try:
            return jsonify(
                AutorService.delete(autor_id, g.current_user_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar autor")

    # -------- RELACIÓN AUTOR - LIBRO --------

    @staticmethod
    def add_libro(autor_id):
        try:
            data = request.get_json()
            return jsonify(
                AutorService.add_libro(
                    autor_id,
                    data["libro_id"],
                    g.current_user_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="asociar libro a autor")

    @staticmethod
    def remove_libro(autor_id, libro_id):
        try:
            return jsonify(
                AutorService.remove_libro(
                    autor_id,
                    libro_id,
                    g.current_user_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="desasociar libro de autor")
