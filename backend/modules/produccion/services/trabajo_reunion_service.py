from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, registro_puntual_en_memoria,
)
from modules.produccion.services.trabajo_enlace import validar_enlace
from datetime import datetime

from sqlalchemy import or_

from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.produccion.models.trabajo_autor import TrabajoReunionAutor
from modules.produccion.services.trabajo_autores_service import (
    validar_autores, validar_referencias, sincronizar_autores, filtrar_por_autor,
)
from modules.produccion.models.trabajo_reunion import (
    TrabajoReunionCientifica,
    TipoReunion,
    TrabajoReunionCientificaMemoriaVersion,
)
from modules.shared.services.auditoria_service import AuditoriaService
from modules.memorias.services.memoria_periodo_service import esta_en_periodo_memoria
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE
from extension import db
from modules.shared.services.text_validation import has_letter


class TrabajoReunionCientificaService:

    @staticmethod
    def _validar_payload(data: dict):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos no pueden estar vacios")

    @staticmethod
    def _normalizar_fecha_payload(data):
        # Compatibilidad temporal con consumidores que aún envían fecha_inicio.
        if "fecha_inicio" not in data:
            return data
        if "fecha_presentacion" in data and data["fecha_presentacion"] != data["fecha_inicio"]:
            raise ValidationError("Las fechas enviadas no coinciden", details={"fields": {
                "fecha_presentacion": "Envíe una única fecha de presentación."}})
        resultado = dict(data)
        resultado["fecha_presentacion"] = resultado.pop("fecha_inicio")
        return resultado

    @staticmethod
    def _validar_id(valor, campo: str, permitir_none: bool = False):
        if valor is None and permitir_none:
            return None

        if not isinstance(valor, int) or valor <= 0:
            if campo == "tipo_reunion_id":
                raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Seleccione un tipo de reunión disponible."}})
            raise ValidationError("No pudimos procesar la solicitud. Intente nuevamente.")

        return valor

    @staticmethod
    def _validar_user_id(user_id: int):
        return TrabajoReunionCientificaService._validar_id(user_id, "user_id")

    @staticmethod
    def _validar_texto(valor, campo, min_len=2, max_len=255):
        labels = {"titulo_trabajo": "el título del trabajo", "nombre_reunion": "el nombre de la reunión", "procedencia": "la procedencia"}
        label = labels.get(campo, "este dato")
        if not isinstance(valor, str) or not valor.strip():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {label}."}})
        if campo == "nombre_reunion" and not has_letter(valor):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "El nombre de la reunión debe contener letras."}})

        valor = " ".join(valor.strip().split())
        if not min_len <= len(valor) <= max_len:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Use entre {min_len} y {max_len} caracteres para {label}."}})

        return valor

    @staticmethod
    def _validar_fecha(fecha_str: str):
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_presentacion": "Ingrese una fecha válida."}})

        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_presentacion": "Ingrese una fecha desde el 01/01/2010."}})
        return fecha

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

        return TrabajoReunionCientificaService._validar_id(valor, campo)

    @staticmethod
    def _validar_grupo(grupo_utn_id):
        grupo_utn_id = TrabajoReunionCientificaService._validar_id(
            grupo_utn_id, "grupo_utn_id", permitir_none=True
        )

        if grupo_utn_id is None:
            return None

        grupo = db.session.get(GrupoInvestigacionUtn, grupo_utn_id)
        if not grupo or getattr(grupo, "deleted_at", None) is not None:
            raise NotFoundError("Grupo UTN invalido")

        return grupo.id

    @staticmethod
    def _validar_tipo_reunion(tipo_reunion_id):
        tipo_reunion_id = TrabajoReunionCientificaService._validar_id(
            tipo_reunion_id, "tipo_reunion_id"
        )
        tipo_reunion = db.session.get(TipoReunion, tipo_reunion_id)
        if not tipo_reunion:
            raise NotFoundError("El tipo de reunión ya no está disponible. Elija otro e intente nuevamente.", details={"fields": {"tipo_reunion_id": "Seleccione un tipo de reunión disponible."}})
        return tipo_reunion.id

    @staticmethod
    def _get_or_404(trabajo_id: int):
        trabajo = db.session.get(
            TrabajoReunionCientifica,
            TrabajoReunionCientificaService._validar_id(trabajo_id, "trabajo_id")
        )
        if not trabajo:
            raise NotFoundError("Trabajo en reunion cientifica no encontrado")
        return trabajo

    @staticmethod
    def _get_activo_or_404(trabajo_id: int):
        trabajo = TrabajoReunionCientificaService._get_or_404(trabajo_id)
        if trabajo.deleted_at is not None:
            raise ConflictError("No se puede operar sobre un trabajo eliminado")
        return trabajo

    @staticmethod
    def _validar_no_duplicado(
        titulo_trabajo: str,
        nombre_reunion: str,
        procedencia: str,
        fecha_presentacion,
        trabajo_id: int = None
    ):
        query = TrabajoReunionCientifica.query.filter(
            TrabajoReunionCientifica.deleted_at.is_(None),
            TrabajoReunionCientifica.titulo_trabajo == titulo_trabajo,
            TrabajoReunionCientifica.nombre_reunion == nombre_reunion,
            TrabajoReunionCientifica.procedencia == procedencia,
            TrabajoReunionCientifica.fecha_presentacion == fecha_presentacion,
        )

        if trabajo_id is not None:
            query = query.filter(TrabajoReunionCientifica.id != trabajo_id)

        if query.first():
            raise ConflictError(
                "Ya existe un trabajo de reunión con los mismos datos. Revise el título, la reunión y la fecha antes de reintentar."
            )

    @staticmethod
    def _list_query(filters: dict = None):
        filters = filters or {}
        query = filtrar_por_autor(TrabajoReunionCientifica.query, TrabajoReunionCientifica, TrabajoReunionAutor, filters)

        activos = TrabajoReunionCientificaService._normalizar_activos(
            filters.get("activos")
        )
        if activos == "true":
            query = query.filter(
                TrabajoReunionCientifica.deleted_at.is_(None),
                TrabajoReunionCientifica.activo.is_(True)
            )
        elif activos == "false":
            query = query.filter(
                or_(
                    TrabajoReunionCientifica.deleted_at.isnot(None),
                    TrabajoReunionCientifica.activo.is_(False)
                )
            )
        elif activos != "all":
            query = query.filter(
                TrabajoReunionCientifica.deleted_at.is_(None),
                TrabajoReunionCientifica.activo.is_(True)
            )

        grupo_utn_id = TrabajoReunionCientificaService._parse_int_filter(
            filters.get("grupo_utn_id"), "grupo_utn_id"
        )
        if grupo_utn_id is not None:
            query = query.filter(TrabajoReunionCientifica.grupo_utn_id == grupo_utn_id)

        orden = TrabajoReunionCientificaService._normalizar_orden(
            filters.get("orden")
        )
        if orden == "asc":
            query = query.order_by(TrabajoReunionCientifica.fecha_presentacion.asc())
        else:
            query = query.order_by(TrabajoReunionCientifica.fecha_presentacion.desc())

        return query.order_by(TrabajoReunionCientifica.id.desc())

    @staticmethod
    def get_all(filters: dict = None):
        return [t.serialize() for t in TrabajoReunionCientificaService._list_query(filters).all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = TrabajoReunionCientificaService._list_query(filters)
        total = query.count()
        return [t.serialize() for t in query.offset((page - 1) * per_page).limit(per_page).all()], total

    @staticmethod
    def get_by_id(trabajo_id: int):
        return TrabajoReunionCientificaService._get_or_404(trabajo_id).serialize()

    @staticmethod
    def get_historial(trabajo_id: int):
        trabajo = TrabajoReunionCientificaService._get_or_404(trabajo_id)
        return AuditoriaService.obtener_historial_entidad(
            entidad="trabajo_reunion_cientifica",
            registro_id=trabajo.id
        )

    @staticmethod
    def create(data: dict, user_id: int):
        TrabajoReunionCientificaService._validar_payload(data)
        data = TrabajoReunionCientificaService._normalizar_fecha_payload(data)
        TrabajoReunionCientificaService._validar_user_id(user_id)

        fecha_presentacion = TrabajoReunionCientificaService._validar_fecha(
            data.get("fecha_presentacion")
        )
        titulo = TrabajoReunionCientificaService._validar_texto(
            data.get("titulo_trabajo"), "titulo_trabajo", 5, 300
        )
        nombre_reunion = TrabajoReunionCientificaService._validar_texto(
            data.get("nombre_reunion"), "nombre_reunion", 3
        )
        procedencia = TrabajoReunionCientificaService._validar_texto(
            data.get("procedencia"), "procedencia", 2
        )
        tipo_reunion_id = TrabajoReunionCientificaService._validar_tipo_reunion(
            data.get("tipo_reunion_id")
        )
        grupo_utn_id = TrabajoReunionCientificaService._validar_grupo(
            data.get("grupo_utn_id")
        )

        TrabajoReunionCientificaService._validar_no_duplicado(
            titulo,
            nombre_reunion,
            procedencia,
            fecha_presentacion,
        )

        enlace = validar_enlace(data.get("enlace"))
        autores = validar_autores(data.get("autores", []))

        trabajo = TrabajoReunionCientifica(
            titulo_trabajo=titulo,
            nombre_reunion=nombre_reunion,
            procedencia=procedencia,
            fecha_presentacion=fecha_presentacion,
            tipo_reunion_id=tipo_reunion_id,
            grupo_utn_id=grupo_utn_id,
            enlace=enlace,
            created_by=user_id
        )

        try:
            db.session.add(trabajo)
            db.session.flush()
            sincronizar_autores(trabajo, autores, TrabajoReunionAutor, "trabajo_reunion_cientifica", user_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return trabajo.serialize()

    @staticmethod
    def update(trabajo_id: int, data: dict, user_id: int):
        TrabajoReunionCientificaService._validar_payload(data)
        data = TrabajoReunionCientificaService._normalizar_fecha_payload(data)
        TrabajoReunionCientificaService._validar_user_id(user_id)
        trabajo = TrabajoReunionCientificaService._get_activo_or_404(trabajo_id)
        autores = validar_autores(data["autores"], trabajo.autorias) if "autores" in data else None
        enlace = validar_enlace(data["enlace"]) if "enlace" in data else trabajo.enlace
        cambios = {}

        fecha_presentacion = trabajo.fecha_presentacion
        if "fecha_presentacion" in data:
            fecha_presentacion = TrabajoReunionCientificaService._validar_fecha(
                data["fecha_presentacion"]
            )

        titulo = trabajo.titulo_trabajo
        if "titulo_trabajo" in data:
            titulo = TrabajoReunionCientificaService._validar_texto(
                data["titulo_trabajo"], "titulo_trabajo", 5, 300
            )

        nombre_reunion = trabajo.nombre_reunion
        if "nombre_reunion" in data:
            nombre_reunion = TrabajoReunionCientificaService._validar_texto(
                data["nombre_reunion"], "nombre_reunion", 3
            )

        procedencia = trabajo.procedencia
        if "procedencia" in data:
            procedencia = TrabajoReunionCientificaService._validar_texto(
                data["procedencia"], "procedencia", 2
            )

        tipo_reunion_id = trabajo.tipo_reunion_id
        if "tipo_reunion_id" in data:
            tipo_reunion_id = TrabajoReunionCientificaService._validar_tipo_reunion(
                data["tipo_reunion_id"]
            )

        grupo_utn_id = trabajo.grupo_utn_id
        if "grupo_utn_id" in data:
            grupo_utn_id = TrabajoReunionCientificaService._validar_grupo(
                data["grupo_utn_id"]
            )

        TrabajoReunionCientificaService._validar_no_duplicado(
            titulo,
            nombre_reunion,
            procedencia,
            fecha_presentacion,
            trabajo.id,
        )

        try:
            cambio = AuditoriaService.construir_cambio(
                trabajo.fecha_presentacion,
                fecha_presentacion
            )
            if cambio:
                cambios["fecha_presentacion"] = cambio
                trabajo.fecha_presentacion = fecha_presentacion

            cambio = AuditoriaService.construir_cambio(
                trabajo.titulo_trabajo,
                titulo
            )
            if cambio:
                cambios["titulo_trabajo"] = cambio
                trabajo.titulo_trabajo = titulo

            cambio = AuditoriaService.construir_cambio(
                trabajo.nombre_reunion,
                nombre_reunion
            )
            if cambio:
                cambios["nombre_reunion"] = cambio
                trabajo.nombre_reunion = nombre_reunion

            cambio = AuditoriaService.construir_cambio(
                trabajo.procedencia,
                procedencia
            )
            if cambio:
                cambios["procedencia"] = cambio
                trabajo.procedencia = procedencia

            cambio = AuditoriaService.construir_cambio(
                trabajo.tipo_reunion_id,
                tipo_reunion_id
            )
            if cambio:
                cambios["tipo_reunion_id"] = cambio
                trabajo.tipo_reunion_id = tipo_reunion_id

            cambio = AuditoriaService.construir_cambio(
                trabajo.grupo_utn_id,
                grupo_utn_id
            )
            if cambio:
                cambios["grupo_utn_id"] = cambio
                trabajo.grupo_utn_id = grupo_utn_id

            cambio = AuditoriaService.construir_cambio(trabajo.enlace, enlace)
            if cambio:
                cambios["enlace"] = cambio
                trabajo.enlace = enlace

            if cambios:
                trabajo.mark_updated(user_id)
                AuditoriaService.registrar_cambios(
                    entidad="trabajo_reunion_cientifica",
                    registro_id=trabajo.id,
                    cambios=cambios,
                    user_id=user_id
                )

            if autores is not None:
                sincronizar_autores(trabajo, autores, TrabajoReunionAutor, "trabajo_reunion_cientifica", user_id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return trabajo.serialize()

    @staticmethod
    def delete(trabajo_id: int, user_id: int):
        TrabajoReunionCientificaService._validar_user_id(user_id)
        trabajo = TrabajoReunionCientificaService._get_activo_or_404(trabajo_id)
        trabajo.soft_delete(user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Trabajo eliminado correctamente (soft delete)"}

    @staticmethod
    def restore(trabajo_id: int):
        trabajo = TrabajoReunionCientificaService._get_or_404(trabajo_id)

        if trabajo.deleted_at is None and trabajo.activo is True:
            raise ConflictError("El trabajo ya se encuentra activo")

        trabajo.restore()
        trabajo.activo = True

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return trabajo.serialize()

    @staticmethod
    def desvincular_autores(trabajo_id, autores, user_id):
        TrabajoReunionCientificaService._validar_user_id(user_id)
        trabajo = TrabajoReunionCientificaService._get_activo_or_404(trabajo_id)
        claves = set(validar_referencias(autores))
        restantes = [{"rol": a.rol, "id": a.integrante.id} for a in trabajo.autorias
                     if (a.rol, a.integrante.id) not in claves]
        return TrabajoReunionCientificaService.update(trabajo_id, {"autores": restantes}, user_id)

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        trabajos = consultar_entidades_memoria(TrabajoReunionCientifica, memoria_version)

        snapshots = []
        for trabajo in trabajos:
            if not registro_puntual_en_memoria(memoria_version, trabajo, trabajo.fecha_presentacion):
                continue
            autores = [autor.serialize() for autor in trabajo.autorias]

            snapshot = TrabajoReunionCientificaMemoriaVersion(
                memoria_version_id=memoria_version.id,
                trabajo_reunion_id=trabajo.id,
                enlace=trabajo.enlace,
                titulo_trabajo=trabajo.titulo_trabajo,
                nombre_reunion=trabajo.nombre_reunion,
                procedencia=trabajo.procedencia,
                fecha_presentacion=trabajo.fecha_presentacion,
                tipo_reunion_id=trabajo.tipo_reunion_id,
                tipo_reunion_nombre=(
                    trabajo.tipo_reunion_cientifica.nombre
                    if trabajo.tipo_reunion_cientifica else None
                ),
                grupo_utn_id=trabajo.grupo_utn_id,
                grupo_utn_nombre=(
                    trabajo.grupo_utn.nombre_sigla_grupo
                    if trabajo.grupo_utn else None
                ),
                autores=autores,
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            TrabajoReunionCientificaMemoriaVersion.query
            .filter(
                TrabajoReunionCientificaMemoriaVersion.memoria_version_id == memoria_version_id,
                TrabajoReunionCientificaMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(
                TrabajoReunionCientificaMemoriaVersion.fecha_presentacion.desc(),
                TrabajoReunionCientificaMemoriaVersion.id.desc()
            )
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
