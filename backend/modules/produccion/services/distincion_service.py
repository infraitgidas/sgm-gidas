from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from datetime import date, datetime

from sqlalchemy import or_

from modules.produccion.models.distinciones import (
    DistincionRecibida,
    DistincionRecibidaMemoriaVersion,
)
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion
from modules.shared.services.auditoria_service import AuditoriaService
from modules.memorias.services.memoria_periodo_service import esta_en_periodo_memoria
from extension import db
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE


class DistincionRecibidaService:

    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")

    @staticmethod
    def _validar_id(valor, campo: str):
        if not isinstance(valor, int) or valor <= 0:
            if campo == "proyecto_investigacion_id":
                raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Seleccione un proyecto disponible."}})
            raise ValidationError("No pudimos procesar la solicitud. Intente nuevamente.")
        return valor

    @staticmethod
    def _validar_texto(valor: str, campo: str):
        if not isinstance(valor, str) or not valor.strip():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese la descripción de la distinción."}})
        return " ".join(valor.strip().split())

    @staticmethod
    def _validar_user_id(user_id: int):
        return DistincionRecibidaService._validar_id(user_id, "user_id")

    @staticmethod
    def _normalizar_activos(activos):
        if activos is None:
            return "true"
        return str(activos).strip().lower()

    @staticmethod
    def _normalizar_orden(orden):
        if orden is None:
            return None
        return str(orden).strip().lower()

    @staticmethod
    def _parse_int_filter(valor, campo: str):
        if valor is None or valor == "":
            return None

        try:
            valor = int(valor)
        except (TypeError, ValueError):
            raise ValidationError(f"El campo '{campo}' debe ser un entero positivo")

        return DistincionRecibidaService._validar_id(valor, campo)

    @staticmethod
    def _validar_fecha(fecha_str: str):
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha": "Ingrese una fecha válida."}})

        if fecha > date.today():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha": "Ingrese una fecha que no sea futura."}})

        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha": "Ingrese una fecha desde el 01/01/2010."}})
        return fecha

    @staticmethod
    def _validar_proyecto(proyecto_id):
        proyecto_id = DistincionRecibidaService._validar_id(
            proyecto_id, "proyecto_investigacion_id"
        )
        proyecto = db.session.get(ProyectoInvestigacion, proyecto_id)
        if not proyecto or proyecto.deleted_at is not None:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"proyecto_investigacion_id": "Seleccione un proyecto disponible."}})
        return proyecto.id

    @staticmethod
    def _get_or_404(distincion_id: int):
        distincion = db.session.get(
            DistincionRecibida,
            DistincionRecibidaService._validar_id(distincion_id, "distincion_id")
        )
        if not distincion:
            raise NotFoundError("Distincion no encontrada")
        return distincion

    @staticmethod
    def _get_activa_or_404(distincion_id: int):
        distincion = DistincionRecibidaService._get_or_404(distincion_id)
        if distincion.deleted_at is not None:
            raise NotFoundError("Distincion no encontrada")
        return distincion

    @staticmethod
    def _validar_no_duplicado(
        proyecto_id: int,
        descripcion: str,
        fecha,
        distincion_id: int = None
    ):
        query = DistincionRecibida.query.filter(
            DistincionRecibida.proyecto_investigacion_id == proyecto_id,
            DistincionRecibida.descripcion == descripcion,
            DistincionRecibida.fecha == fecha,
            DistincionRecibida.deleted_at.is_(None)
        )

        if distincion_id is not None:
            query = query.filter(DistincionRecibida.id != distincion_id)

        if query.first():
            raise ConflictError(
                "Ya existe una distinción igual para ese proyecto y fecha. Revise los datos e intente nuevamente."
            )

    @staticmethod
    def _list_query(filters: dict = None):
        filters = filters or {}
        query = DistincionRecibida.query

        proyecto_id = DistincionRecibidaService._parse_int_filter(
            filters.get("proyecto_id"), "proyecto_id"
        )
        if proyecto_id is not None:
            query = query.filter(
                DistincionRecibida.proyecto_investigacion_id == proyecto_id
            )

        activos = DistincionRecibidaService._normalizar_activos(
            filters.get("activos")
        )
        if activos == "true":
            query = query.filter(
                DistincionRecibida.deleted_at.is_(None),
                DistincionRecibida.activo.is_(True)
            )
        elif activos == "false":
            query = query.filter(
                or_(
                    DistincionRecibida.deleted_at.isnot(None),
                    DistincionRecibida.activo.is_(False)
                )
            )
        elif activos != "all":
            query = query.filter(
                DistincionRecibida.deleted_at.is_(None),
                DistincionRecibida.activo.is_(True)
            )

        orden = DistincionRecibidaService._normalizar_orden(filters.get("orden"))
        if orden == "asc":
            query = query.order_by(DistincionRecibida.fecha.asc())
        else:
            query = query.order_by(DistincionRecibida.fecha.desc())

        return query.order_by(DistincionRecibida.id.desc())

    @staticmethod
    def get_all(filters: dict = None):
        return [d.serialize() for d in DistincionRecibidaService._list_query(filters).all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = DistincionRecibidaService._list_query(filters)
        total = query.count()
        return [d.serialize() for d in query.offset((page - 1) * per_page).limit(per_page).all()], total

    @staticmethod
    def get_by_id(distincion_id: int):
        return DistincionRecibidaService._get_or_404(distincion_id).serialize()

    @staticmethod
    def get_historial(distincion_id: int):
        distincion = DistincionRecibidaService._get_or_404(distincion_id)
        return AuditoriaService.obtener_historial_entidad(
            entidad="distincion_recibida",
            registro_id=distincion.id
        )

    @staticmethod
    def create(data: dict, user_id: int):
        DistincionRecibidaService._validar_payload(data)
        DistincionRecibidaService._validar_user_id(user_id)

        fecha = DistincionRecibidaService._validar_fecha(data.get("fecha"))
        descripcion = DistincionRecibidaService._validar_texto(
            data.get("descripcion"), "descripcion"
        )
        proyecto_id = DistincionRecibidaService._validar_proyecto(
            data.get("proyecto_investigacion_id")
        )

        DistincionRecibidaService._validar_no_duplicado(
            proyecto_id,
            descripcion,
            fecha
        )

        dist = DistincionRecibida(
            fecha=fecha,
            descripcion=descripcion,
            proyecto_investigacion_id=proyecto_id,
            created_by=user_id
        )

        db.session.add(dist)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return dist.serialize()

    @staticmethod
    def update(distincion_id: int, data: dict, user_id: int):
        DistincionRecibidaService._validar_payload(data)
        DistincionRecibidaService._validar_user_id(user_id)
        dist = DistincionRecibidaService._get_activa_or_404(distincion_id)
        cambios = {}

        fecha = dist.fecha
        if "fecha" in data:
            fecha = DistincionRecibidaService._validar_fecha(data["fecha"])

        descripcion = dist.descripcion
        if "descripcion" in data:
            descripcion = DistincionRecibidaService._validar_texto(
                data["descripcion"], "descripcion"
            )

        proyecto_id = dist.proyecto_investigacion_id
        if "proyecto_investigacion_id" in data:
            proyecto_id = DistincionRecibidaService._validar_proyecto(
                data["proyecto_investigacion_id"]
            )

        DistincionRecibidaService._validar_no_duplicado(
            proyecto_id,
            descripcion,
            fecha,
            dist.id
        )

        cambio = AuditoriaService.construir_cambio(dist.fecha, fecha)
        if cambio:
            cambios["fecha"] = cambio
            dist.fecha = fecha

        cambio = AuditoriaService.construir_cambio(dist.descripcion, descripcion)
        if cambio:
            cambios["descripcion"] = cambio
            dist.descripcion = descripcion

        cambio = AuditoriaService.construir_cambio(
            dist.proyecto_investigacion_id,
            proyecto_id
        )
        if cambio:
            cambios["proyecto_investigacion_id"] = cambio
            dist.proyecto_investigacion_id = proyecto_id

        if cambios:
            dist.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="distincion_recibida",
                registro_id=dist.id,
                cambios=cambios,
                user_id=user_id
            )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return dist.serialize()

    @staticmethod
    def delete(distincion_id: int, user_id: int):
        DistincionRecibidaService._validar_user_id(user_id)

        dist = DistincionRecibidaService._get_activa_or_404(distincion_id)
        dist.soft_delete(user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Distincion eliminada correctamente"}

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        distinciones = consultar_entidades_memoria(DistincionRecibida, memoria_version, relacion="proyecto_investigacion")

        snapshots = []
        for distincion in distinciones:
            if not registro_puntual_en_memoria(memoria_version, distincion, distincion.fecha):
                continue
            snapshot = DistincionRecibidaMemoriaVersion(
                memoria_version_id=memoria_version.id,
                distincion_id=distincion.id,
                fecha=distincion.fecha,
                descripcion=distincion.descripcion,
                proyecto_investigacion_id=distincion.proyecto_investigacion_id,
                proyecto_codigo=(
                    distincion.proyecto_investigacion.codigo_proyecto
                    if distincion.proyecto_investigacion else None
                ),
                proyecto_nombre=(
                    distincion.proyecto_investigacion.nombre_proyecto
                    if distincion.proyecto_investigacion else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            DistincionRecibidaMemoriaVersion.query
            .filter(
                DistincionRecibidaMemoriaVersion.memoria_version_id == memoria_version_id,
                DistincionRecibidaMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(
                DistincionRecibidaMemoriaVersion.fecha.desc(),
                DistincionRecibidaMemoriaVersion.id.desc()
            )
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
