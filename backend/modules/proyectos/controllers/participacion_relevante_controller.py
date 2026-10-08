from flask import g, jsonify, request

from modules.proyectos.services.participacion_relevante_service import ParticipacionRelevanteService
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, filtered_page_response


class ParticipacionRelevanteController:
    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                return filtered_page_response(ParticipacionRelevanteService, request.args.to_dict(), request.args)
            return jsonify(ParticipacionRelevanteService.get_all(request.args.to_dict())), 200
        except Exception as error:
            return exception_response(error, operation="listar participaciones relevantes")

    @staticmethod
    def get_by_id(participacion_id):
        try:
            return jsonify(ParticipacionRelevanteService.get_by_id(participacion_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar participacion relevante")

    @staticmethod
    def get_historial(participacion_id):
        try:
            return jsonify(ParticipacionRelevanteService.get_historial(participacion_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial de participacion relevante")

    @staticmethod
    def create():
        try:
            return jsonify(ParticipacionRelevanteService.create(request.get_json(), g.current_user_id)), 201
        except Exception as error:
            return exception_response(error, operation="crear participacion relevante")

    @staticmethod
    def update(participacion_id):
        try:
            return jsonify(ParticipacionRelevanteService.update(participacion_id, request.get_json(), g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="actualizar participacion relevante")

    @staticmethod
    def delete(participacion_id):
        try:
            return jsonify(ParticipacionRelevanteService.delete(participacion_id, g.current_user_id)), 200
        except Exception as error:
            return exception_response(error, operation="eliminar participacion relevante")
