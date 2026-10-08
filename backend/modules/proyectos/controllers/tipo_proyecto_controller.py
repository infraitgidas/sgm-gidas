from flask import g, jsonify, request

from modules.proyectos.models.proyecto_investigacion import TipoProyecto
from modules.proyectos.services.tipo_proyecto_service import TipoProyectoService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


class TipoProyectoController:
    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(TipoProyectoService, request.args)
            return jsonify(TipoProyectoService.get_all(request.args.get("activos", "true"))), 200
        except Exception as error:
            return exception_response(error, operation="listar tipos de proyecto")

    @staticmethod
    def get_by_id(tipo_id):
        try:
            return jsonify(TipoProyectoService.get_by_id(tipo_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar tipo de proyecto")

    @staticmethod
    def get_historial(tipo_id):
        try:
            return jsonify(CatalogoAuditoriaService.historial_por_modelo(TipoProyecto, tipo_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de proyecto")

    @staticmethod
    def create():
        try:
            return jsonify(TipoProyectoService.create(request.get_json(), getattr(g, "current_user_id", None))), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de proyecto")

    @staticmethod
    def update(tipo_id):
        try:
            return jsonify(TipoProyectoService.update(tipo_id, request.get_json(), getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de proyecto")

    @staticmethod
    def delete(tipo_id):
        try:
            return jsonify(TipoProyectoService.delete(tipo_id, getattr(g, "current_user_id", None))), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de proyecto")
