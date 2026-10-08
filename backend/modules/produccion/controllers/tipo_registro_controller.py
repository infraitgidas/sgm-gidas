from flask import jsonify, request, g
from modules.produccion.services.tipo_registro_service import TipoRegistroPropiedadService
from modules.produccion.models.registro_patente import TipoRegistroPropiedad
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, catalog_page_response

class TipoRegistroPropiedadController:

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return catalog_page_response(TipoRegistroPropiedadService, request.args)
            return jsonify(
                TipoRegistroPropiedadService.get_all(request.args.get("activos", "true"))
            ), 200
        except Exception as error:
            return exception_response(error, operation="listar tipos de registro")

    @staticmethod
    def get_by_id(tipo_id):
        try:
            return jsonify(TipoRegistroPropiedadService.get_by_id(tipo_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar tipo de registro")

    @staticmethod
    def get_historial(tipo_id):
        try:
            return jsonify(
                CatalogoAuditoriaService.historial_por_modelo(
                    TipoRegistroPropiedad,
                    tipo_id
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de tipo de registro")

    @staticmethod
    def create():
        try:
            data = request.get_json()
            return jsonify(
                TipoRegistroPropiedadService.create(
                    data,
                    getattr(g, "current_user_id", None)
                )
            ), 201
        except Exception as error:
            return exception_response(error, operation="crear tipo de registro")

    @staticmethod
    def update(tipo_id):
        try:
            data = request.get_json()
            return jsonify(
                TipoRegistroPropiedadService.update(
                    tipo_id,
                    data,
                    getattr(g, "current_user_id", None)
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="actualizar tipo de registro")

    @staticmethod
    def delete(tipo_id):
        try:
            return jsonify(
                TipoRegistroPropiedadService.delete(
                    tipo_id,
                    getattr(g, "current_user_id", None)
                )
            ), 200
        except Exception as error:
            return exception_response(error, operation="eliminar tipo de registro")
