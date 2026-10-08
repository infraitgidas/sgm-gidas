from flask import jsonify, request, g
from modules.produccion.services.documentacion_service import (
    DocumentacionBibliograficaService
)
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, filtered_page_response, table_page_response

class DocumentacionBibliograficaController:

    @staticmethod
    def get_all():
        try:
            filters = {
                "activos": request.args.get("activos", "true"),
                "orden": request.args.get("orden")
            }
            if request.args.get("view") == "table":
                return table_page_response(DocumentacionBibliograficaService, filters, request.args)
            if pagination_requested(request.args):
                return filtered_page_response(DocumentacionBibliograficaService, filters, request.args)
            return jsonify(
                DocumentacionBibliograficaService.get_all(filters)
            ), 200
        except Exception as error:
            return exception_response(error, operation="listar documentacion bibliografica")


    @staticmethod
    def get_by_id(doc_id):
        try:
            return jsonify(
                DocumentacionBibliograficaService.get_by_id(doc_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar documentacion bibliografica")

    @staticmethod
    def get_historial(doc_id):
        try:
            return jsonify(
                DocumentacionBibliograficaService.get_historial(doc_id)
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de documentacion")


    @staticmethod
    def create():
        try:
            data = request.get_json()
            user_id = g.current_user_id

            return jsonify(
                DocumentacionBibliograficaService.create(data, user_id)
            ), 201

        except Exception as error:
            return exception_response(error, operation="crear documentacion bibliografica")


    @staticmethod
    def update(doc_id):
        try:
            data = request.get_json()
            user_id = g.current_user_id

            return jsonify(
                DocumentacionBibliograficaService.update(doc_id, data, user_id)
            ), 200

        except Exception as error:
            return exception_response(error, operation="actualizar documentacion bibliografica")


    @staticmethod
    def delete(doc_id):
        try:
            user_id = g.current_user_id

            return jsonify(
                DocumentacionBibliograficaService.delete(doc_id, user_id)
            ), 200

        except Exception as error:
            return exception_response(error, operation="eliminar documentacion bibliografica")


    # -------- RELACIÓN DOCUMENTO - AUTOR --------

    @staticmethod
    def add_autor(doc_id):
        try:
            data = request.get_json()

            return jsonify(
                DocumentacionBibliograficaService.add_autor(
                    doc_id,
                    data["autor_id"],
                    g.current_user_id
                )
            ), 200

        except Exception as error:
            return exception_response(error, operation="asociar autor a documentacion")


    @staticmethod
    def remove_autor(doc_id, autor_id):
        try:
            return jsonify(
                DocumentacionBibliograficaService.remove_autor(
                    doc_id,
                    autor_id,
                    g.current_user_id
                )
            ), 200

        except Exception as error:
            return exception_response(error, operation="desasociar autor de documentacion")
