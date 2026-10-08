import builtins
from datetime import date, datetime
import unicodedata

from extension import db
from sqlalchemy.orm import joinedload
from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria,
    registro_puntual_en_memoria,
)
from modules.personal.models.personal import Becario, Investigador
from modules.proyectos.models.participacion_relevante import (
    ParticipacionRelevante,
    ParticipacionRelevanteMemoriaVersion,
)
from modules.shared.exceptions import ConflictError, NotFoundError
from modules.shared.exceptions import ValidationError as ValueError
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from modules.shared.services.text_validation import has_letter


def normalizar_texto(texto: str) -> str:
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


class ParticipacionRelevanteService:
    ROLES_PARTICIPANTE = {"investigador": Investigador, "becario": Becario}

    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValueError("Los datos no pueden estar vacíos")

    @staticmethod
    def _validar_id(valor, campo: str):
        if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
            if campo in {"investigador_id", "participante_id"}:
                raise ValueError(
                    "Revise el participante e intente nuevamente.",
                    details={"fields": {"participante": "Seleccione un participante disponible."}},
                )
            raise ValueError("No pudimos procesar la solicitud. Intente nuevamente.")
        return valor

    @staticmethod
    def _normalizar_activos(activos):
        return "true" if activos is None else str(activos).strip().lower()

    @staticmethod
    def _normalizar_orden(orden):
        return None if orden is None else str(orden).strip().lower()

    @staticmethod
    def _parse_int_filter(valor, campo: str):
        if valor is None or valor == "":
            return None
        try:
            valor = int(valor)
        except (TypeError, builtins.ValueError):
            raise ValueError(f"El campo '{campo}' debe ser un entero positivo")
        return ParticipacionRelevanteService._validar_id(valor, campo)

    @staticmethod
    def _validar_texto(valor: str, campo: str):
        nombres = {
            "nombre_evento": "nombre del evento",
            "forma_participacion": "forma de participación",
        }
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(
                f"Revise {nombres[campo]} e intente nuevamente.",
                details={"fields": {campo: f"Ingrese {nombres[campo]}."}},
            )
        if campo == "nombre_evento" and not has_letter(valor):
            raise ValueError(
                "Revise los campos indicados e intente nuevamente.",
                details={"fields": {campo: "El nombre del evento debe contener letras."}},
            )
        return valor.strip()

    @staticmethod
    def _validar_user_id(user_id: int):
        return ParticipacionRelevanteService._validar_id(user_id, "user_id")

    @staticmethod
    def _validar_fecha(fecha_str: str):
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, builtins.ValueError):
            raise ValueError(
                "Revise la fecha e intente nuevamente.",
                details={"fields": {"fecha": "Ingrese una fecha válida."}},
            )
        if fecha > date.today():
            raise ValueError(
                "Revise la fecha e intente nuevamente.",
                details={"fields": {"fecha": "Ingrese una fecha que no sea futura."}},
            )
        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValueError(
                "Revise la fecha e intente nuevamente.",
                details={"fields": {"fecha": "Ingrese una fecha desde el 01/01/2010."}},
            )
        return fecha

    @staticmethod
    def _validar_participante(data: dict, requerido=True):
        referencia = data.get("participante")
        if referencia is None and "investigador_id" in data:
            referencia = {"rol": "investigador", "id": data.get("investigador_id")}
        if referencia is None:
            if requerido:
                raise ValueError(
                    "Revise el participante e intente nuevamente.",
                    details={"fields": {"participante": "Seleccione un investigador o becario."}},
                )
            return None
        if not isinstance(referencia, dict):
            raise ValueError(
                "Revise el participante e intente nuevamente.",
                details={"fields": {"participante": "Seleccione un participante válido."}},
            )
        rol = str(referencia.get("rol") or "").strip().lower()
        if rol not in ParticipacionRelevanteService.ROLES_PARTICIPANTE:
            raise ValueError(
                "Revise el participante e intente nuevamente.",
                details={"fields": {"participante": "Seleccione un investigador o becario."}},
            )
        participante_id = ParticipacionRelevanteService._validar_id(
            referencia.get("id"), "participante_id"
        )
        participante = db.session.get(
            ParticipacionRelevanteService.ROLES_PARTICIPANTE[rol], participante_id
        )
        if (
            participante is None
            or participante.deleted_at is not None
            or not getattr(participante, "activo", True)
        ):
            raise NotFoundError(
                "La persona seleccionada ya no está disponible. Elija otra e intente nuevamente.",
                details={"fields": {"participante": "Seleccione un participante disponible."}},
            )
        return rol, participante_id, participante

    @staticmethod
    def _get_or_404(participacion_id: int):
        participacion = db.session.get(
            ParticipacionRelevante,
            ParticipacionRelevanteService._validar_id(participacion_id, "participacion_id"),
        )
        if not participacion:
            raise NotFoundError("Participación relevante no encontrada")
        return participacion

    @staticmethod
    def _get_activa_or_404(participacion_id: int):
        participacion = ParticipacionRelevanteService._get_or_404(participacion_id)
        if participacion.deleted_at is not None:
            raise NotFoundError("Participación relevante no encontrada")
        return participacion

    @staticmethod
    def _validar_no_duplicado(
        participante_rol: str,
        participante_id: int,
        nombre_evento: str,
        forma_participacion: str,
        fecha,
        participacion_id: int = None,
    ):
        columna = (
            ParticipacionRelevante.investigador_id
            if participante_rol == "investigador"
            else ParticipacionRelevante.becario_id
        )
        query = ParticipacionRelevante.query.filter(
            ParticipacionRelevante.deleted_at.is_(None),
            columna == participante_id,
            ParticipacionRelevante.nombre_evento == nombre_evento,
            ParticipacionRelevante.forma_participacion == forma_participacion,
            ParticipacionRelevante.fecha == fecha,
        )
        if participacion_id is not None:
            query = query.filter(ParticipacionRelevante.id != participacion_id)
        if query.first():
            raise ConflictError(
                "Ya existe una participación igual para esa persona y fecha. Revise los datos e intente nuevamente."
            )

    @staticmethod
    def _list_query(filters: dict = None):
        filters = filters or {}
        query = ParticipacionRelevante.query.options(
            joinedload(ParticipacionRelevante.investigador),
            joinedload(ParticipacionRelevante.becario),
        )
        investigador_id = ParticipacionRelevanteService._parse_int_filter(
            filters.get("investigador_id"), "investigador_id"
        )
        if investigador_id is not None:
            query = query.filter(ParticipacionRelevante.investigador_id == investigador_id)

        participante_rol = str(filters.get("participante_rol") or "").strip().lower()
        participante_id = ParticipacionRelevanteService._parse_int_filter(
            filters.get("participante_id"), "participante_id"
        )
        if participante_rol or participante_id is not None:
            if participante_rol not in ParticipacionRelevanteService.ROLES_PARTICIPANTE or participante_id is None:
                raise ValueError("Los filtros de participante deben enviarse juntos y ser válidos.")
            columna = (
                ParticipacionRelevante.investigador_id
                if participante_rol == "investigador"
                else ParticipacionRelevante.becario_id
            )
            query = query.filter(columna == participante_id)

        activos = ParticipacionRelevanteService._normalizar_activos(filters.get("activos"))
        if activos == "true":
            query = query.filter(ParticipacionRelevante.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(ParticipacionRelevante.deleted_at.isnot(None))
        elif activos != "all":
            query = query.filter(ParticipacionRelevante.deleted_at.is_(None))

        orden = ParticipacionRelevanteService._normalizar_orden(filters.get("orden"))
        columna_orden = ParticipacionRelevante.fecha.asc() if orden == "asc" else ParticipacionRelevante.fecha.desc()
        return query.order_by(columna_orden, ParticipacionRelevante.id.desc())

    @staticmethod
    def get_all(filters: dict = None):
        return [p.serialize() for p in ParticipacionRelevanteService._list_query(filters).all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = ParticipacionRelevanteService._list_query(filters)
        total = query.count()
        return [p.serialize() for p in query.offset((page - 1) * per_page).limit(per_page).all()], total

    @staticmethod
    def get_by_id(participacion_id: int):
        return ParticipacionRelevanteService._get_or_404(participacion_id).serialize()

    @staticmethod
    def get_historial(participacion_id: int):
        participacion = ParticipacionRelevanteService._get_or_404(participacion_id)
        return AuditoriaService.obtener_historial_entidad(
            entidad="participacion_relevante", registro_id=participacion.id
        )

    @staticmethod
    def create(data: dict, user_id: int):
        ParticipacionRelevanteService._validar_payload(data)
        ParticipacionRelevanteService._validar_user_id(user_id)
        nombre_evento = normalizar_texto(
            ParticipacionRelevanteService._validar_texto(data.get("nombre_evento"), "nombre_evento")
        )
        forma_participacion = normalizar_texto(
            ParticipacionRelevanteService._validar_texto(data.get("forma_participacion"), "forma_participacion")
        )
        fecha = ParticipacionRelevanteService._validar_fecha(data.get("fecha"))
        participante_rol, participante_id, _ = ParticipacionRelevanteService._validar_participante(data)
        ParticipacionRelevanteService._validar_no_duplicado(
            participante_rol, participante_id, nombre_evento, forma_participacion, fecha
        )
        participacion = ParticipacionRelevante(
            nombre_evento=nombre_evento,
            forma_participacion=forma_participacion,
            fecha=fecha,
            investigador_id=participante_id if participante_rol == "investigador" else None,
            becario_id=participante_id if participante_rol == "becario" else None,
            created_by=user_id,
        )
        db.session.add(participacion)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return participacion.serialize()

    @staticmethod
    def update(participacion_id: int, data: dict, user_id: int):
        ParticipacionRelevanteService._validar_payload(data)
        ParticipacionRelevanteService._validar_user_id(user_id)
        part = ParticipacionRelevanteService._get_activa_or_404(participacion_id)

        nombre_evento = part.nombre_evento
        if "nombre_evento" in data:
            nombre_evento = normalizar_texto(
                ParticipacionRelevanteService._validar_texto(data["nombre_evento"], "nombre_evento")
            )
        forma_participacion = part.forma_participacion
        if "forma_participacion" in data:
            forma_participacion = normalizar_texto(
                ParticipacionRelevanteService._validar_texto(data["forma_participacion"], "forma_participacion")
            )
        fecha = part.fecha
        if "fecha" in data:
            fecha = ParticipacionRelevanteService._validar_fecha(data["fecha"])

        participante_nuevo = ParticipacionRelevanteService._validar_participante(data, requerido=False)
        participante_rol = participante_nuevo[0] if participante_nuevo else part.participante_rol
        participante_id = participante_nuevo[1] if participante_nuevo else (part.investigador_id or part.becario_id)
        ParticipacionRelevanteService._validar_no_duplicado(
            participante_rol, participante_id, nombre_evento, forma_participacion, fecha, part.id
        )

        cambios = {}
        for campo, nuevo_valor in (
            ("nombre_evento", nombre_evento),
            ("forma_participacion", forma_participacion),
            ("fecha", fecha),
        ):
            if campo in data:
                cambio = AuditoriaService.construir_cambio(getattr(part, campo), nuevo_valor)
                if cambio:
                    cambios[campo] = cambio
                    setattr(part, campo, nuevo_valor)

        if participante_nuevo:
            participante_anterior = {
                "rol": part.participante_rol,
                "id": part.investigador_id or part.becario_id,
                "nombre_apellido": part.participante.nombre_apellido if part.participante else None,
            }
            participante_actual = {
                "rol": participante_rol,
                "id": participante_id,
                "nombre_apellido": participante_nuevo[2].nombre_apellido,
            }
            cambio = AuditoriaService.construir_cambio(participante_anterior, participante_actual)
            if cambio:
                cambios["participante"] = cambio
                part.investigador_id = participante_id if participante_rol == "investigador" else None
                part.becario_id = participante_id if participante_rol == "becario" else None

        if cambios:
            part.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="participacion_relevante",
                registro_id=part.id,
                cambios=cambios,
                user_id=user_id,
            )
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return part.serialize()

    @staticmethod
    def delete(participacion_id: int, user_id: int):
        ParticipacionRelevanteService._validar_user_id(user_id)
        part = ParticipacionRelevanteService._get_activa_or_404(participacion_id)
        part.soft_delete(user_id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return {"message": "Participación relevante eliminada correctamente"}

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        participaciones = (
            consultar_entidades_memoria(ParticipacionRelevante, memoria_version, relacion="investigador")
            + consultar_entidades_memoria(ParticipacionRelevante, memoria_version, relacion="becario")
        )
        snapshots = []
        for participacion in participaciones:
            if not registro_puntual_en_memoria(memoria_version, participacion, participacion.fecha):
                continue
            snapshot = ParticipacionRelevanteMemoriaVersion(
                memoria_version_id=memoria_version.id,
                participacion_relevante_id=participacion.id,
                nombre_evento=participacion.nombre_evento,
                forma_participacion=participacion.forma_participacion,
                fecha=participacion.fecha,
                investigador_id=participacion.investigador_id,
                becario_id=participacion.becario_id,
                investigador_nombre=(participacion.investigador.nombre_apellido if participacion.investigador else None),
                becario_nombre=(participacion.becario.nombre_apellido if participacion.becario else None),
                created_by=user_id,
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)
        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            ParticipacionRelevanteMemoriaVersion.query
            .filter(
                ParticipacionRelevanteMemoriaVersion.memoria_version_id == memoria_version_id,
                ParticipacionRelevanteMemoriaVersion.deleted_at.is_(None),
            )
            .order_by(ParticipacionRelevanteMemoriaVersion.fecha.desc())
            .all()
        )
        return [snapshot.serialize() for snapshot in snapshots]
