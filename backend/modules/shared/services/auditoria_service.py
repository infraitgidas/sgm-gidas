from datetime import date, datetime
from enum import Enum
from flask import g, has_request_context, request
from sqlalchemy import select

from extension import db
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.services.date_time import serialize_temporal
from modules.shared.exceptions import NotFoundError
from modules.shared.exceptions import ValidationError
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.services.tenant_scope import _classes_by_table, _predicate


HISTORY_TABLE_ALIASES = {
    "visita_academica": "visita_grupo",
    "registro_propiedad": "registros_patente_grupo",
    "trabajo_revista_referato": "trabajos_revista",
}


class AuditoriaService:

    @staticmethod
    def _normalizar_valor(valor):
        if isinstance(valor, (datetime, date)):
            return serialize_temporal(valor)

        if isinstance(valor, Enum):
            return valor.value

        return valor

    @staticmethod
    def construir_cambio(valor_anterior, valor_nuevo):
        valor_anterior = AuditoriaService._normalizar_valor(valor_anterior)
        valor_nuevo = AuditoriaService._normalizar_valor(valor_nuevo)

        if valor_anterior == valor_nuevo:
            return None

        return {
            "valor_anterior": valor_anterior,
            "valor_nuevo": valor_nuevo
        }

    @staticmethod
    def registrar_cambios(
        entidad: str,
        registro_id: int,
        cambios: dict,
        user_id: int | None = None,
        memoria_id: int | None = None,
        memoria_version_id: int | None = None
    ):
        # Recibe solo los campos que ya cambiaron y persiste una fila por
        # atributo para facilitar filtros y trazabilidad fina.
        for campo, valores in cambios.items():
            if not valores:
                continue

            auditoria = AuditoriaCampo(
                entidad=entidad,
                registro_id=registro_id,
                campo=campo,
                valor_anterior=valores.get("valor_anterior"),
                valor_nuevo=valores.get("valor_nuevo"),
                usuario_id=user_id,
                memoria_id=memoria_id,
                memoria_version_id=memoria_version_id
            )
            db.session.add(auditoria)

    @staticmethod
    def registrar_evento_relacion(
        entidad: str,
        registro_id: int,
        relacion: str,
        accion: str,
        detalle: dict,
        user_id: int | None = None,
        memoria_id: int | None = None,
        memoria_version_id: int | None = None
    ):
        # Registra altas y bajas de asociaciones con un payload compacto
        # para reconstruir el contexto del vínculo.
        auditoria = AuditoriaCampo(
            entidad=entidad,
            registro_id=registro_id,
            campo=relacion,
            valor_anterior=None,
            valor_nuevo={
                "accion": accion,
                "detalle": {
                    clave: AuditoriaService._normalizar_valor(valor)
                    for clave, valor in (detalle or {}).items()
                }
            },
            usuario_id=user_id,
            memoria_id=memoria_id,
            memoria_version_id=memoria_version_id
        )
        db.session.add(auditoria)

    @staticmethod
    def obtener_historial_entidad(entidad: str, registro_id: int, *, paginate: bool = True,
                                 extra_filter=None):
        group_id = getattr(g, "current_grupo_utn_id", None) if has_request_context() else None
        if group_id is not None:
            classes = _classes_by_table()
            model = classes.get(HISTORY_TABLE_ALIASES.get(entidad, entidad))
            if model is None:
                raise NotFoundError("Historial no encontrado")
            predicate = _predicate(model, group_id, classes)
            if predicate is not None and db.session.execute(
                select(model.id).where(model.id == registro_id, predicate)
            ).scalar_one_or_none() is None:
                raise NotFoundError("Historial no encontrado")
        query = (
            AuditoriaCampo.query
            .filter(
                AuditoriaCampo.entidad == entidad,
                AuditoriaCampo.registro_id == registro_id
            )
            .order_by(
                AuditoriaCampo.fecha_cambio.desc(),
                AuditoriaCampo.id.desc()
            )
        )
        if extra_filter is not None:
            query = query.filter(extra_filter)
        if paginate and has_request_context() and pagination_requested(request.args):
            args = request.args.to_dict()
            args.setdefault("per_page", "3")
            try:
                params = parse_pagination_params(args)
            except ValueError as error:
                raise ValidationError(str(error)) from error
            total = query.count()
            historial = query.offset((params["page"] - 1) * params["per_page"]).limit(
                params["per_page"]
            ).all()
            return {
                "data": [item.serialize() for item in historial],
                "meta": {
                    "page": params["page"], "per_page": params["per_page"],
                    "total": total,
                    "total_pages": max(1, (total + params["per_page"] - 1) // params["per_page"]),
                    "activos": params["activos"], "orden": params["orden"],
                    "source": "legacy-list",
                },
                "error": None,
            }
        return [item.serialize() for item in query.all()]
