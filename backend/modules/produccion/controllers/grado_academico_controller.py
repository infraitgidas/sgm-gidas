from flask import g, jsonify, request

from modules.produccion.models.actividad_docencia import GradoAcademico
from modules.produccion.services.grado_academico_service import GradoAcademicoService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class GradoAcademicoController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(GradoAcademicoService, request.args)
            return jsonify(
                GradoAcademicoService.get_all(request.args.get("activos", "true"))
            ), 200
        except Exception as error:
            return exception_response(error, operation="listar grados academicos")

    @staticmethod
    def get_by_id(grado_id):
        try:
            return jsonify(GradoAcademicoService.get_by_id(grado_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar grado academico")

    @staticmethod
    def get_historial(grado_id):
        try:
            return jsonify(
                CatalogoAuditoriaService.historial_por_modelo(
                    GradoAcademico,
                    grado_id,
                )
            ), 200
        except Exception as error:
            return exception_response(
                error,
                operation="consultar historial de grado academico",
            )

    @staticmethod
    def create():
        data = request.get_json()
        try:
            return jsonify(
                GradoAcademicoService.create(
                    data,
                    getattr(g, "current_user_id", None),
                )
            ), 201
        except Exception as error:
            return exception_response(error, operation="crear grado academico")

    @staticmethod
    def update(grado_id):
        data = request.get_json()
        try:
            return jsonify(
                GradoAcademicoService.update(
                    grado_id,
                    data,
                    getattr(g, "current_user_id", None),
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="actualizar grado academico")

    @staticmethod
    def delete(grado_id):
        try:
            return jsonify(
                GradoAcademicoService.delete(
                    grado_id,
                    getattr(g, "current_user_id", None),
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar grado academico")
