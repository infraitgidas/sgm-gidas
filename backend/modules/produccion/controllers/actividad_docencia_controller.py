from flask import jsonify, request, g
from modules.produccion.services.actividad_docencia_service import (
    ActividadDocenciaService
)
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, filtered_page_response, table_page_response


class ActividadDocenciaController:

    @staticmethod
    def get_all():
        try:
            filtros = {
                "investigador_id": request.args.get("investigador_id", type=int),
                "orden": request.args.get("orden"),
                "activos": request.args.get("activos", "true")
            }

            if request.args.get("view") == "table":
                return table_page_response(ActividadDocenciaService, filtros, request.args)
            if pagination_requested(request.args):
                return filtered_page_response(ActividadDocenciaService, filtros, request.args)
            return jsonify(
                ActividadDocenciaService.get_all(filtros)
            ), 200

        except Exception as error:
            return exception_response(error, operation="listar actividades de docencia")

    @staticmethod
    def get_by_id(actividad_id):
        try:
            return jsonify(
                ActividadDocenciaService.get_by_id(actividad_id)
            ), 200

        except Exception as error:
            return exception_response(error, operation="consultar actividad de docencia")

    @staticmethod
    def get_historial(actividad_id):
        try:
            return jsonify(
                ActividadDocenciaService.get_historial(actividad_id)
            ), 200

        except Exception as error:
            return exception_response(error, operation="consultar historial de actividad docente")

    @staticmethod
    def create():
        try:
            data = request.get_json()

            return jsonify(
                ActividadDocenciaService.create(
                    data,
                    user_id=g.current_user_id
                )
            ), 201

        except Exception as error:
            return exception_response(error, operation="crear actividad de docencia")

    @staticmethod
    def update(actividad_id):
        try:
            data = request.get_json()

            return jsonify(
                ActividadDocenciaService.update(
                    actividad_id,
                    data,
                    user_id=g.current_user_id
                )
            ), 200

        except Exception as error:
            return exception_response(error, operation="actualizar actividad de docencia")

    @staticmethod
    def delete(actividad_id):
        try:
            return jsonify(
                ActividadDocenciaService.delete(
                    actividad_id,
                    user_id=g.current_user_id
                )
            ), 200

        except Exception as error:
            return exception_response(error, operation="eliminar actividad de docencia")
