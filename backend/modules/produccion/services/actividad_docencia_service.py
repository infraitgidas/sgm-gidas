from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, fin_vigencia,
)
from datetime import date, datetime
from flask import has_request_context, request
from sqlalchemy import String, case, cast, func, literal, select, union_all
from sqlalchemy.orm import joinedload, selectinload

from modules.produccion.models.actividad_docencia import (
    ActividadDocencia,
    ActividadDocenciaGradoMemoriaVersion,
    ActividadDocenciaMemoriaVersion,
    GradoAcademico,
    InvestigadorActividadGrado,
    RolActividad,
)
from modules.personal.models.personal import Investigador
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.controllers.pagination import pagination_requested, parse_pagination_params
from modules.shared.controllers.pagination import table_query_page, table_scope_predicate
from modules.memorias.services.memoria_periodo_service import estuvo_activo_en_periodo_memoria
from extension import db
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.date_time import INSTITUTIONAL_MIN_DATE


class ActividadDocenciaService:

    @staticmethod
    def _validar_payload(data):
        if not isinstance(data, dict) or not data:
            raise ValidationError("Los datos enviados son invalidos")

    @staticmethod
    def _validar_user_id(user_id):
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError("No pudimos procesar la solicitud. Intente nuevamente.")
        return user_id

    @staticmethod
    def _validar_id(valor, campo):
        if not isinstance(valor, int) or valor <= 0:
            if campo in {"investigador_id", "grado_academico_id", "rol_actividad_id"}:
                raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Seleccione una opción disponible."}})
            raise ValidationError("No pudimos procesar la solicitud. Intente nuevamente.")
        return valor

    @staticmethod
    def _validar_texto(valor, campo, min_len=2, max_len=255):
        labels = {"curso": "el curso", "institucion": "la institución"}
        label = labels.get(campo, "este dato")
        if not isinstance(valor, str) or not valor.strip():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Ingrese {label}."}})

        valor = " ".join(valor.strip().split())
        if not min_len <= len(valor) <= max_len:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: f"Use entre {min_len} y {max_len} caracteres para {label}."}})

        return valor

    @staticmethod
    def _parse_fecha(valor, campo):
        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese una fecha válida."}})
        if fecha < INSTITUTIONAL_MIN_DATE:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {campo: "Ingrese una fecha desde el 01/01/2010."}})
        return fecha

    @staticmethod
    def _validar_fechas(fecha_inicio, fecha_fin):
        if fecha_inicio > date.today():
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_inicio": "Ingrese una fecha de inicio que no sea futura."}})

        if fecha_fin < fecha_inicio:
            raise ValidationError("Revise los campos indicados e intente nuevamente.", details={"fields": {"fecha_fin": "Ingrese una fecha de fin igual o posterior al inicio."}})

    @staticmethod
    def _normalizar_activos(activos):
        if activos is None:
            return "true"
        return str(activos).strip().lower()

    @staticmethod
    def _get_or_404(model, obj_id, message, permitir_eliminado=False):
        obj = db.session.get(model, obj_id)
        if not obj or (not permitir_eliminado and getattr(obj, "deleted_at", None) is not None):
            fields = {Investigador: "investigador_id", GradoAcademico: "grado_academico_id", RolActividad: "rol_actividad_id"}
            if model in fields:
                raise NotFoundError("La opción seleccionada ya no está disponible. Elija otra e intente nuevamente.", details={"fields": {fields[model]: "Seleccione una opción disponible."}})
            raise NotFoundError(message)
        return obj

    @staticmethod
    def _obtener_actividad(actividad_id, permitir_eliminado=True):
        actividad_id = ActividadDocenciaService._validar_id(
            actividad_id, "actividad_id"
        )
        return ActividadDocenciaService._get_or_404(
            ActividadDocencia,
            actividad_id,
            "Actividad de docencia no encontrada",
            permitir_eliminado=permitir_eliminado
        )

    @staticmethod
    def _obtener_historial_activo_unico(actividad_id):
        historiales = InvestigadorActividadGrado.query.filter_by(
            actividad_docencia_id=actividad_id,
            fecha_fin=None
        ).all()

        if len(historiales) > 1:
            raise ConflictError(
                "La actividad tiene mas de un historial de grado activo"
            )

        return historiales[0] if historiales else None

    @staticmethod
    def _obtener_grado_activo_desde_actividad(actividad):
        historial_activo = next(
            (
                item for item in getattr(actividad, "investigadores_grado", [])
                if item.fecha_fin is None
            ),
            None
        )
        return historial_activo.grado_academico if historial_activo else None

    @staticmethod
    def _validar_grado(grado_id):
        grado_id = ActividadDocenciaService._validar_id(
            grado_id, "grado_academico_id"
        )
        return ActividadDocenciaService._get_or_404(
            GradoAcademico,
            grado_id,
            "Grado academico invalido"
        )

    @staticmethod
    def _validar_rol(rol_id):
        rol_id = ActividadDocenciaService._validar_id(
            rol_id, "rol_actividad_id"
        )
        return ActividadDocenciaService._get_or_404(
            RolActividad,
            rol_id,
            "Rol de actividad invalido"
        )

    @staticmethod
    def _validar_investigador(investigador_id):
        investigador_id = ActividadDocenciaService._validar_id(
            investigador_id, "investigador_id"
        )
        return ActividadDocenciaService._get_or_404(
            Investigador,
            investigador_id,
            "Investigador invalido"
        )

    @staticmethod
    def _validar_no_duplicado(
        investigador_id,
        curso,
        institucion,
        fecha_inicio,
        fecha_fin,
        rol_actividad_id,
        actividad_id=None,
    ):
        query = ActividadDocencia.query.filter(
            ActividadDocencia.deleted_at.is_(None),
            ActividadDocencia.investigador_id == investigador_id,
            ActividadDocencia.curso == curso,
            ActividadDocencia.institucion == institucion,
            ActividadDocencia.fecha_inicio == fecha_inicio,
            ActividadDocencia.fecha_fin == fecha_fin,
            ActividadDocencia.rol_actividad_id == rol_actividad_id,
        )

        if actividad_id is not None:
            query = query.filter(ActividadDocencia.id != actividad_id)

        if query.first():
            raise ConflictError(
                "Ya existe una actividad de docencia con los mismos datos para ese investigador"
            )

    @staticmethod
    def _list_query(filters: dict = None):
        filters = filters or {}
        query = ActividadDocencia.query.options(
            joinedload(ActividadDocencia.investigador).load_only(
                Investigador.id, Investigador.nombre_apellido, Investigador.deleted_at,
            ).lazyload("*"),
            joinedload(ActividadDocencia.rol_actividad),
            selectinload(ActividadDocencia.investigadores_grado)
            .joinedload(InvestigadorActividadGrado.grado_academico),
        )

        investigador_id = filters.get("investigador_id")
        if investigador_id is not None:
            investigador_id = ActividadDocenciaService._validar_id(
                investigador_id, "investigador_id"
            )
            query = query.filter(ActividadDocencia.investigador_id == investigador_id)

        activos = ActividadDocenciaService._normalizar_activos(filters.get("activos"))
        if activos == "true":
            query = query.filter(ActividadDocencia.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(ActividadDocencia.deleted_at.isnot(None))
        elif activos != "all":
            query = query.filter(ActividadDocencia.deleted_at.is_(None))

        orden = filters.get("orden")
        if orden == "asc":
            query = query.order_by(ActividadDocencia.fecha_inicio.asc())
        else:
            query = query.order_by(ActividadDocencia.fecha_inicio.desc())

        return query.order_by(ActividadDocencia.id.desc())

    @staticmethod
    def get_all(filters: dict = None):
        return [a.serialize() for a in ActividadDocenciaService._list_query(filters).all()]

    @staticmethod
    def get_page(filters: dict, page: int, per_page: int):
        query = ActividadDocenciaService._list_query(filters)
        total = query.count()
        return [a.serialize() for a in query.offset((page - 1) * per_page).limit(per_page).all()], total

    @staticmethod
    def get_table_page(filters, args):
        grade = select(GradoAcademico.nombre).join(
            InvestigadorActividadGrado,
            InvestigadorActividadGrado.grado_academico_id == GradoAcademico.id,
        ).where(
            InvestigadorActividadGrado.actividad_docencia_id == ActividadDocencia.id,
            InvestigadorActividadGrado.fecha_fin.is_(None),
            table_scope_predicate(InvestigadorActividadGrado),
        ).order_by(InvestigadorActividadGrado.fecha_inicio.desc(),
                   InvestigadorActividadGrado.id.desc()).limit(1).scalar_subquery()
        query = ActividadDocenciaService._list_query(filters).outerjoin(
            ActividadDocencia.investigador,
        ).outerjoin(ActividadDocencia.rol_actividad)
        fields = {"curso": ActividadDocencia.curso, "institucion": ActividadDocencia.institucion,
                  "investigador": case((Investigador.deleted_at.is_(None), Investigador.nombre_apellido), else_=""),
                  "rol": RolActividad.nombre, "grado": grade,
                  "fecha_inicio": ActividadDocencia.fecha_inicio,
                  "estado": ActividadDocencia.deleted_at.isnot(None)}
        return table_query_page(query, ActividadDocencia, args, fields,
                                default_sort="fecha_inicio",
                                searchable=("curso", "institucion", "investigador", "rol", "grado"),
                                facets=("curso", "institucion", "investigador", "rol", "grado"))

    @staticmethod
    def get_by_id(actividad_id: int):
        return ActividadDocenciaService._obtener_actividad(
            actividad_id,
            permitir_eliminado=True
        ).serialize()

    @staticmethod
    def get_historial(actividad_id: int):
        actividad = ActividadDocenciaService._obtener_actividad(
            actividad_id,
            permitir_eliminado=True
        )
        if has_request_context() and pagination_requested(request.args):
            return ActividadDocenciaService._historial_page(actividad.id)
        historial = AuditoriaService.obtener_historial_entidad(
            entidad="actividad_y_catedra_posgrado",
            registro_id=actividad.id,
            paginate=False,
        )
        historial_filtrado = [
            item for item in historial
            if item.get("campo") != "grado_academico_id"
        ]
        historial_filtrado.extend(
            ActividadDocenciaService._construir_historial_grados(actividad)
        )
        historial_filtrado.sort(
            key=lambda item: (
                item.get("fecha_cambio") or "",
                item.get("orden_historial") or 0
            ),
            reverse=True
        )

        for item in historial_filtrado:
            item.pop("orden_historial", None)

        return historial_filtrado

    @staticmethod
    def _historial_page(actividad_id: int):
        args = request.args.to_dict()
        args.setdefault("per_page", "3")
        try:
            params = parse_pagination_params(args)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        grades = select(
            InvestigadorActividadGrado.id.label("id"),
            InvestigadorActividadGrado.fecha_inicio.label("fecha_inicio"),
            func.lag(InvestigadorActividadGrado.grado_academico_id).over(
                order_by=(InvestigadorActividadGrado.fecha_inicio.asc(), InvestigadorActividadGrado.id.asc())
            ).label("previous_grade_id"),
        ).where(InvestigadorActividadGrado.actividad_docencia_id == actividad_id).subquery()
        audit = select(
            literal("audit").label("source"), AuditoriaCampo.id.label("id"),
            cast(AuditoriaCampo.fecha_cambio, String).label("sort_key"),
            AuditoriaCampo.id.label("tie"), literal(None).label("previous_grade_id"),
        ).where(
            AuditoriaCampo.entidad == "actividad_y_catedra_posgrado",
            AuditoriaCampo.registro_id == actividad_id,
            AuditoriaCampo.campo != "grado_academico_id",
        )
        grade_events = select(
            literal("grade").label("source"), grades.c.id,
            cast(grades.c.fecha_inicio, String).label("sort_key"),
            grades.c.id.label("tie"), grades.c.previous_grade_id,
        ).where(grades.c.previous_grade_id.isnot(None))
        events = union_all(audit, grade_events).subquery()
        total = db.session.scalar(select(func.count()).select_from(events))
        rows = db.session.execute(
            select(events).order_by(events.c.sort_key.desc(), events.c.tie.desc())
            .offset((params["page"] - 1) * params["per_page"]).limit(params["per_page"])
        ).all()
        data = []
        for row in rows:
            if row.source == "audit":
                data.append(db.session.get(AuditoriaCampo, row.id).serialize())
                continue
            item = db.session.get(InvestigadorActividadGrado, row.id)
            previous_grade = db.session.get(GradoAcademico, row.previous_grade_id)
            data.append({
                "id": f"historial-grado-{item.id}", "tipo": "historial_grado",
                "entidad": "actividad_y_catedra_posgrado", "registro_id": actividad_id,
                "campo": "grado_academico_id",
                "valor_anterior": ActividadDocenciaService._serializar_grado(previous_grade),
                "valor_nuevo": ActividadDocenciaService._serializar_grado(item.grado_academico),
                "fecha_cambio": item.fecha_inicio.isoformat(),
                "usuario_id": item.created_by,
                "usuario_nombre": item.created_by_user.nombre_usuario if item.created_by_user else None,
                "activo": item.fecha_fin is None,
                "fecha_fin": item.fecha_fin.isoformat() if item.fecha_fin else None,
                "detalle": item.serialize(),
            })
        return {
            "data": data,
            "meta": {
                "page": params["page"], "per_page": params["per_page"], "total": total,
                "total_pages": max(1, (total + params["per_page"] - 1) // params["per_page"]),
                "activos": params["activos"], "orden": params["orden"], "source": "legacy-list",
            },
            "error": None,
        }

    @staticmethod
    def _serializar_grado(grado):
        if not grado:
            return None

        return {
            "id": grado.id,
            "nombre": grado.nombre
        }

    @staticmethod
    def _construir_historial_grados(actividad):
        historial = sorted(
            getattr(actividad, "investigadores_grado", []),
            key=lambda item: (
                item.fecha_inicio or date.min,
                item.id or 0
            )
        )

        eventos = []
        grado_anterior = None

        for orden, item in enumerate(historial):
            grado_actual = ActividadDocenciaService._serializar_grado(
                item.grado_academico
            )
            if orden == 0:
                grado_anterior = grado_actual
                continue

            eventos.append({
                "id": f"historial-grado-{item.id}",
                "tipo": "historial_grado",
                "entidad": "actividad_y_catedra_posgrado",
                "registro_id": getattr(actividad, "id", None),
                "campo": "grado_academico_id",
                "valor_anterior": grado_anterior,
                "valor_nuevo": grado_actual,
                "fecha_cambio": item.fecha_inicio.isoformat(),
                "usuario_id": item.created_by,
                "usuario_nombre": (
                    item.created_by_user.nombre_usuario
                    if item.created_by_user else None
                ),
                "activo": item.fecha_fin is None,
                "fecha_fin": (
                    item.fecha_fin.isoformat()
                    if item.fecha_fin else None
                ),
                # Se usa solo para ordenar eventos de igual fecha y luego se oculta.
                "orden_historial": orden,
                "detalle": item.serialize()
            })
            grado_anterior = grado_actual

        return eventos

    @staticmethod
    def create(data: dict, user_id: int):
        ActividadDocenciaService._validar_payload(data)
        ActividadDocenciaService._validar_user_id(user_id)

        fecha_inicio = ActividadDocenciaService._parse_fecha(
            data.get("fecha_inicio"), "fecha_inicio"
        )
        fecha_fin = ActividadDocenciaService._parse_fecha(
            data.get("fecha_fin"), "fecha_fin"
        )
        ActividadDocenciaService._validar_fechas(fecha_inicio, fecha_fin)

        curso = ActividadDocenciaService._validar_texto(
            data.get("curso"), "curso", min_len=3
        )
        institucion = ActividadDocenciaService._validar_texto(
            data.get("institucion"), "institucion", min_len=3
        )
        grado = ActividadDocenciaService._validar_grado(data.get("grado_academico_id"))
        rol = ActividadDocenciaService._validar_rol(data.get("rol_actividad_id"))
        investigador = ActividadDocenciaService._validar_investigador(
            data.get("investigador_id")
        )

        ActividadDocenciaService._validar_no_duplicado(
            investigador.id,
            curso,
            institucion,
            fecha_inicio,
            fecha_fin,
            rol.id,
        )

        actividad = ActividadDocencia(
            curso=curso,
            institucion=institucion,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            rol_actividad_id=rol.id,
            investigador_id=investigador.id,
            created_by=user_id,
        )

        db.session.add(actividad)
        db.session.flush()

        historial = InvestigadorActividadGrado(
            investigador_id=investigador.id,
            actividad_docencia_id=actividad.id,
            grado_academico_id=grado.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=None,
            created_by=user_id,
        )

        db.session.add(historial)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return actividad.serialize()

    @staticmethod
    def update(actividad_id: int, data: dict, user_id: int = None):
        ActividadDocenciaService._validar_payload(data)

        if user_id is not None:
            ActividadDocenciaService._validar_user_id(user_id)

        actividad = ActividadDocenciaService._obtener_actividad(
            actividad_id,
            permitir_eliminado=False
        )
        cambios = {}

        if "investigador_id" in data and "grado_academico_id" in data:
            raise ConflictError(
                "No se puede actualizar investigador y grado academico en la misma operacion"
            )

        if "investigador_id" in data:
            nuevo_investigador = ActividadDocenciaService._validar_investigador(
                data["investigador_id"]
            )
            if nuevo_investigador.id != actividad.investigador_id:
                raise ConflictError(
                    "No se puede cambiar el investigador de una actividad existente"
                )

        fecha_inicio = actividad.fecha_inicio
        fecha_fin = actividad.fecha_fin
        if "fecha_inicio" in data:
            fecha_inicio = ActividadDocenciaService._parse_fecha(
                data["fecha_inicio"], "fecha_inicio"
            )
        if "fecha_fin" in data:
            fecha_fin = ActividadDocenciaService._parse_fecha(
                data["fecha_fin"], "fecha_fin"
            )

        ActividadDocenciaService._validar_fechas(fecha_inicio, fecha_fin)

        curso = actividad.curso
        if "curso" in data:
            curso = ActividadDocenciaService._validar_texto(
                data["curso"], "curso", min_len=3
            )

        institucion = actividad.institucion
        if "institucion" in data:
            institucion = ActividadDocenciaService._validar_texto(
                data["institucion"], "institucion", min_len=3
            )

        rol_actividad_id = actividad.rol_actividad_id
        if "rol_actividad_id" in data:
            rol_actividad_id = ActividadDocenciaService._validar_rol(
                data["rol_actividad_id"]
            ).id

        ActividadDocenciaService._validar_no_duplicado(
            actividad.investigador_id,
            curso,
            institucion,
            fecha_inicio,
            fecha_fin,
            rol_actividad_id,
            actividad.id,
        )

        for campo, nuevo_valor in (
            ("fecha_inicio", fecha_inicio),
            ("fecha_fin", fecha_fin),
            ("curso", curso),
            ("institucion", institucion),
            ("rol_actividad_id", rol_actividad_id),
        ):
            cambio = AuditoriaService.construir_cambio(
                getattr(actividad, campo),
                nuevo_valor
            )
            if cambio:
                cambios[campo] = cambio
                setattr(actividad, campo, nuevo_valor)

        historial_activo = ActividadDocenciaService._obtener_historial_activo_unico(
            actividad.id
        )

        if historial_activo and historial_activo.fecha_inicio > actividad.fecha_fin:
            raise ConflictError(
                "El historial activo tiene una fecha de inicio invalida respecto de la actividad"
            )

        if "grado_academico_id" in data:
            nuevo_grado = ActividadDocenciaService._validar_grado(
                data["grado_academico_id"]
            )
            cambio = AuditoriaService.construir_cambio(
                historial_activo.grado_academico_id if historial_activo else None,
                nuevo_grado.id
            )

            if not historial_activo:
                nuevo_historial = InvestigadorActividadGrado(
                    investigador_id=actividad.investigador_id,
                    actividad_docencia_id=actividad.id,
                    grado_academico_id=nuevo_grado.id,
                    fecha_inicio=date.today(),
                    fecha_fin=None,
                    created_by=user_id,
                )
                db.session.add(nuevo_historial)
            elif historial_activo.grado_academico_id != nuevo_grado.id:
                if historial_activo.fecha_inicio > date.today():
                    raise ConflictError(
                        "El historial activo tiene una fecha de inicio invalida"
                    )

                historial_activo.fecha_fin = date.today()

                nuevo_historial = InvestigadorActividadGrado(
                    investigador_id=actividad.investigador_id,
                    actividad_docencia_id=actividad.id,
                    grado_academico_id=nuevo_grado.id,
                    fecha_inicio=date.today(),
                    fecha_fin=None,
                    created_by=user_id,
                )
                db.session.add(nuevo_historial)

            if cambio:
                cambios["grado_academico_id"] = cambio

        if cambios and user_id is not None:
            actividad.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="actividad_y_catedra_posgrado",
                registro_id=actividad.id,
                cambios=cambios,
                user_id=user_id
            )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return actividad.serialize()

    @staticmethod
    def delete(actividad_id: int, user_id: int):
        ActividadDocenciaService._validar_user_id(user_id)
        actividad = ActividadDocenciaService._obtener_actividad(
            actividad_id,
            permitir_eliminado=False
        )

        actividad.soft_delete(user_id)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"message": "Actividad de docencia eliminada correctamente"}

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        actividades = consultar_entidades_memoria(ActividadDocencia, memoria_version, relacion="investigador")

        snapshots = []
        for actividad in actividades:
            if not estuvo_activo_en_periodo_memoria(
                memoria_version,
                actividad.fecha_inicio,
                fin_vigencia(actividad)
            ):
                continue
            grado_activo = (
                ActividadDocenciaService._obtener_grado_activo_desde_actividad(
                    actividad
                )
            )
            snapshot = ActividadDocenciaMemoriaVersion(
                memoria_version_id=memoria_version.id,
                actividad_docencia_id=actividad.id,
                curso=actividad.curso,
                institucion=actividad.institucion,
                fecha_inicio=actividad.fecha_inicio,
                fecha_fin=actividad.fecha_fin,
                investigador_id=actividad.investigador_id,
                investigador_nombre=(
                    actividad.investigador.nombre_apellido
                    if actividad.investigador else None
                ),
                rol_actividad_id=actividad.rol_actividad_id,
                rol_actividad_nombre=(
                    actividad.rol_actividad.nombre
                    if actividad.rol_actividad else None
                ),
                grado_academico_id=(
                    grado_activo.id if grado_activo else None
                ),
                grado_academico_nombre=(
                    grado_activo.nombre if grado_activo else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            db.session.flush()

            for historial in getattr(actividad, "investigadores_grado", []):
                if not estuvo_activo_en_periodo_memoria(memoria_version, historial.fecha_inicio, fin_vigencia(historial)):
                    continue
                historial_snapshot = ActividadDocenciaGradoMemoriaVersion(
                    actividad_docencia_memoria_version=snapshot,
                    investigador_actividad_grado_id=historial.id,
                    investigador_id=historial.investigador_id,
                    grado_academico_id=historial.grado_academico_id,
                    grado_academico_nombre=(
                        historial.grado_academico.nombre
                        if historial.grado_academico else None
                    ),
                    fecha_inicio=historial.fecha_inicio,
                    fecha_fin=historial.fecha_fin,
                    created_by=user_id
                )
                db.session.add(historial_snapshot)

            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            ActividadDocenciaMemoriaVersion.query
            .filter(
                ActividadDocenciaMemoriaVersion.memoria_version_id == memoria_version_id,
                ActividadDocenciaMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(ActividadDocenciaMemoriaVersion.curso.asc())
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]
