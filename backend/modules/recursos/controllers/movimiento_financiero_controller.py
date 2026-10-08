from flask import g, jsonify, request

from modules.recursos.models.movimiento_financiero import CategoriaErogacion
from modules.recursos.services.movimiento_financiero_service import MovimientoFinancieroService
from modules.recursos.services.saldo_financiero_service import SaldoFinancieroService
from modules.recursos.services.tipo_cambio_service import TipoCambioService
from modules.shared.exceptions import ValidationError
from modules.shared.controllers.responses import exception_response
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.responses import error_response, paginated_response
from modules.shared.services.catalog_pagination import catalog_page
from modules.shared.controllers.responses import paginated_response
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params


class MovimientoFinancieroController:
    @staticmethod
    def get_cotizacion():
        try:
            fecha = MovimientoFinancieroService._fecha(request.args.get("fecha"))
            return jsonify(TipoCambioService.obtener_vigente_para_fecha(fecha).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar cotización oficial")

    @staticmethod
    def get_all():
        try:
            if pagination_requested(request.args):
                params = parse_pagination_params(request.args)
                data, total = MovimientoFinancieroService.get_page(
                    request.args.to_dict(), params["page"], params["per_page"]
                )
                return paginated_response(
                    data, params["page"], params["per_page"], total,
                    meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"},
                )
            return jsonify(MovimientoFinancieroService.get_all(request.args.to_dict())), 200
        except ValueError as error:
            return exception_response(ValidationError(str(error)), operation="listar movimientos financieros")
        except Exception as error:
            return exception_response(error, operation="listar movimientos financieros")

    @staticmethod
    def get_by_id(movimiento_id):
        try:
            return jsonify(MovimientoFinancieroService.get_by_id(movimiento_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar movimiento financiero")

    @staticmethod
    def get_historial(movimiento_id):
        try:
            return jsonify(MovimientoFinancieroService.get_historial(movimiento_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar historial financiero")

    @staticmethod
    def get_resumen(grupo_id):
        try:
            return jsonify(SaldoFinancieroService.calcular(grupo_id).serialize()), 200
        except Exception as error:
            return exception_response(error, operation="consultar saldo financiero")

    @staticmethod
    def get_saldos_por_fuente(grupo_id):
        try:
            return jsonify(SaldoFinancieroService.saldos_por_fuente(grupo_id)), 200
        except Exception as error:
            return exception_response(error, operation="consultar saldos por fuente")

    @staticmethod
    def get_equipamientos_disponibles(grupo_id):
        try:
            raw_movimiento_id = request.args.get("movimiento_id")
            if raw_movimiento_id is not None and (not raw_movimiento_id.isdecimal() or int(raw_movimiento_id) <= 0):
                raise ValidationError("El movimiento indicado no es válido.")
            movimiento_id = int(raw_movimiento_id) if raw_movimiento_id is not None else None
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as exc:
                    return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
                data, total = MovimientoFinancieroService.equipamientos_disponibles(
                    grupo_id, movimiento_id, params["page"], params["per_page"]
                )
                return paginated_response(data, params["page"], params["per_page"], total,
                                          meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"})
            return jsonify(MovimientoFinancieroService.equipamientos_disponibles(
                grupo_id, movimiento_id
            )), 200
        except Exception as error:
            return exception_response(error, operation="consultar equipamiento disponible")

    @staticmethod
    def get_categorias():
        try:
            if pagination_requested(request.args):
                try:
                    params = parse_pagination_params(request.args)
                except ValueError as exc:
                    return error_response("VALIDATION_ERROR", message=str(exc), status_code=400)
                data, total = catalog_page(
                    CategoriaErogacion, CategoriaErogacion.nombre,
                    activos="true", orden=params["orden"], page=params["page"], per_page=params["per_page"],
                )
                return paginated_response(data, params["page"], params["per_page"], total,
                                          meta={"activos": params["activos"], "orden": params["orden"], "source": "legacy-list"})
            categorias = CategoriaErogacion.query.filter(
                CategoriaErogacion.deleted_at.is_(None)
            ).order_by(CategoriaErogacion.nombre.asc()).all()
            return jsonify([categoria.serialize() for categoria in categorias]), 200
        except Exception as error:
            return exception_response(error, operation="listar categorías de erogación")

    @staticmethod
    def create():
        try:
            return jsonify(MovimientoFinancieroService.create(
                request.get_json(), g.current_user_id,
            )), 201
        except Exception as error:
            return exception_response(error, operation="crear movimiento financiero")

    @staticmethod
    def update(movimiento_id):
        try:
            return jsonify(MovimientoFinancieroService.update(
                movimiento_id, request.get_json(), g.current_user_id,
            )), 200
        except Exception as error:
            return exception_response(error, operation="actualizar movimiento financiero")

    @staticmethod
    def delete(movimiento_id):
        try:
            return jsonify(MovimientoFinancieroService.delete(
                movimiento_id, g.current_user_id,
            )), 200
        except Exception as error:
            return exception_response(error, operation="eliminar movimiento financiero")
