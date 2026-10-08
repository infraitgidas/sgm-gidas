"""Reglas de informes privados y sus vinculos historicos."""
from datetime import date

from flask import g

from extension import db
from sqlalchemy import func, or_
from modules.informes.models.informe import Informe, InformeInvestigador, InformeProyecto
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.memorias.models.memorias import Memoria
from modules.personal.models.personal import Investigador
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import validate_institutional_date


TIPOS = {"investigadores", "pid", "uct"}
TEXTOS = ("titulo", "resumen", "actividades", "resultados", "observaciones")


class InformeService:
    @staticmethod
    def candidates(tipo, memoria_id, search="", page=1, per_page=9):
        InformeService._tipo(tipo)
        if tipo == "uct":
            raise ValidationError("El informe UCT no requiere vinculaciones.")
        if type(page) is not int or page < 1 or type(per_page) is not int or not 1 <= per_page <= 9:
            raise ValidationError("Revise la paginación solicitada.")
        memoria = InformeService._memoria(memoria_id)
        term = str(search or "").strip()[:100].lower()
        if tipo == "investigadores":
            query = Investigador.query.filter(
                Investigador.grupo_utn_id == memoria.grupo_utn_id,
                or_(Investigador.fecha_alta_grupo.is_(None), Investigador.fecha_alta_grupo <= memoria.periodo_fin),
            )
            if term:
                query = query.filter(func.lower(Investigador.nombre_apellido).like(f"%{term}%"))
            query = query.order_by(Investigador.nombre_apellido, Investigador.id)
            name = lambda item: item.nombre_apellido
        else:
            query = ProyectoInvestigacion.query.filter(
                ProyectoInvestigacion.grupo_utn_id == memoria.grupo_utn_id,
                ProyectoInvestigacion.fecha_inicio <= memoria.periodo_fin,
                or_(ProyectoInvestigacion.fecha_fin.is_(None), ProyectoInvestigacion.fecha_fin >= memoria.periodo_inicio),
            )
            if term:
                pattern = f"%{term}%"
                query = query.filter(or_(func.lower(ProyectoInvestigacion.nombre_proyecto).like(pattern), func.lower(ProyectoInvestigacion.codigo_proyecto).like(pattern)))
            query = query.order_by(ProyectoInvestigacion.nombre_proyecto, ProyectoInvestigacion.id)
            name = lambda item: f"{item.codigo_proyecto} · {item.nombre_proyecto}"
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        return [{"id": item.id, "name": name(item), "activo": bool(item.activo and item.deleted_at is None)} for item in rows], total

    @staticmethod
    def _grupo_id():
        grupo_id = getattr(g, "current_grupo_utn_id", None)
        if grupo_id is None:
            raise NotFoundError("Informe no encontrado")
        return grupo_id

    @staticmethod
    def _tipo(tipo):
        if tipo not in TIPOS:
            raise NotFoundError("Tipo de informe no encontrado")
        return tipo

    @staticmethod
    def _informe(tipo, informe_id, *, activo=True):
        InformeService._tipo(tipo)
        if type(informe_id) is not int or informe_id <= 0:
            raise NotFoundError("Informe no encontrado")
        query = Informe.query.filter_by(id=informe_id, tipo=tipo, grupo_utn_id=InformeService._grupo_id())
        if activo:
            query = query.filter(Informe.deleted_at.is_(None))
        informe = query.first()
        if informe is None:
            raise NotFoundError("Informe no encontrado")
        return informe

    @staticmethod
    def _memoria(memoria_id):
        if type(memoria_id) is not int or memoria_id <= 0:
            raise ValidationError("Seleccione una Memoria válida.", details={"fields": {"memoria_id": "Seleccione una Memoria válida."}})
        memoria = Memoria.query.filter_by(id=memoria_id, grupo_utn_id=InformeService._grupo_id()).filter(
            Memoria.deleted_at.is_(None)
        ).first()
        if memoria is None:
            raise ValidationError("Seleccione una Memoria disponible.", details={"fields": {"memoria_id": "Seleccione una Memoria disponible."}})
        return memoria

    @staticmethod
    def _fecha(value):
        try:
            fecha = date.fromisoformat(value) if isinstance(value, str) else value
            if not isinstance(fecha, date):
                raise ValueError("Fecha inválida")
            validate_institutional_date(fecha, "fecha_realizacion")
        except (ValueError, TypeError) as error:
            raise ValidationError("Seleccione una fecha válida.", details={"fields": {"fecha_realizacion": "Seleccione una fecha válida."}}) from error
        if fecha > date.today():
            raise ValidationError("La fecha no puede ser futura.", details={"fields": {"fecha_realizacion": "Seleccione una fecha hasta hoy."}})
        return fecha

    @staticmethod
    def _texto(value, field):
        limit = 200 if field == "titulo" else 20000
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
            raise ValidationError("Complete los campos indicados.", details={"fields": {field: f"Ingrese entre 1 y {limit} caracteres."}})
        return value.strip()

    @staticmethod
    def _ids(ids, tipo):
        if tipo == "uct":
            if ids not in (None, []):
                raise ValidationError("El informe UCT no admite vinculaciones.")
            return []
        if not isinstance(ids, list) or not ids or any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
            raise ValidationError("Seleccione registros válidos sin duplicados.", details={"fields": {"vinculos_ids": "Seleccione al menos un registro disponible."}})
        return ids

    @staticmethod
    def _snapshot(tipo, entity_id, memoria):
        if tipo == "investigadores":
            entity = Investigador.query.filter_by(id=entity_id, grupo_utn_id=memoria.grupo_utn_id).first()
            if entity is None or (entity.fecha_alta_grupo and entity.fecha_alta_grupo > memoria.periodo_fin):
                raise ValidationError("Seleccione investigadores de la UCT y el período.", details={"fields": {"vinculos_ids": "Revise los investigadores seleccionados."}})
            return {"_version": 1, "nombre_apellido": entity.nombre_apellido, "fecha_alta_grupo": entity.fecha_alta_grupo.isoformat() if entity.fecha_alta_grupo else None, "horas_semanales": entity.horas_semanales}
        entity = ProyectoInvestigacion.query.filter_by(id=entity_id, grupo_utn_id=memoria.grupo_utn_id).first()
        if entity is None or entity.fecha_inicio > memoria.periodo_fin or (entity.fecha_fin and entity.fecha_fin < memoria.periodo_inicio):
            raise ValidationError("Seleccione proyectos de la UCT y el período.", details={"fields": {"vinculos_ids": "Revise los proyectos seleccionados."}})
        return {"_version": 1, "codigo_proyecto": entity.codigo_proyecto, "nombre_proyecto": entity.nombre_proyecto, "descripcion_proyecto": entity.descripcion_proyecto, "fecha_inicio": entity.fecha_inicio.isoformat(), "fecha_fin": entity.fecha_fin.isoformat() if entity.fecha_fin else None}

    @staticmethod
    def _uct_snapshot(memoria):
        grupo = db.session.get(GrupoInvestigacionUtn, memoria.grupo_utn_id)
        if grupo is None:
            raise ValidationError("La UCT de la Memoria no está disponible.")
        return {"_version": 1, "nombre_sigla_grupo": grupo.nombre_sigla_grupo, "nombre_unidad_academica": grupo.nombre_unidad_academica, "objetivo_desarrollo": grupo.objetivo_desarrollo, "mail": grupo.mail}

    @staticmethod
    def _sincronizar(informe, ids, user_id, *, inicial=False):
        if informe.tipo == "uct":
            return
        cls, key = (InformeInvestigador, "investigador_id") if informe.tipo == "investigadores" else (InformeProyecto, "proyecto_id")
        all_links = cls.query.filter_by(informe_id=informe.id).all()
        links = {getattr(item, key): item for item in all_links}
        desired = set(ids)
        if informe.tipo == "pid":
            from modules.informes.services.cierre_proyecto import tiene_informe_de_cierre
            for entity_id, link in links.items():
                if entity_id in desired or link.deleted_at is not None:
                    continue
                proyecto = db.session.get(ProyectoInvestigacion, entity_id)
                if proyecto and proyecto.deleted_at and proyecto.fecha_fin and proyecto.fecha_fin <= date.today() and informe.memoria.periodo_inicio <= proyecto.fecha_fin <= informe.memoria.periodo_fin and not tiene_informe_de_cierre(proyecto.id, proyecto.fecha_fin, informe.id, grupo_utn_id=proyecto.grupo_utn_id):
                    raise ConflictError("No puede desvincular un proyecto cerrado de su informe PID.")
        for entity_id in ids:
            current_link = links.get(entity_id)
            if current_link is None or current_link.deleted_at is not None:
                model = Investigador if informe.tipo == "investigadores" else ProyectoInvestigacion
                entity = model.query.filter_by(id=entity_id, grupo_utn_id=informe.grupo_utn_id).first()
                if entity is None:
                    raise ValidationError("Seleccione registros de la UCT.", details={"fields": {"vinculos_ids": "Seleccione registros disponibles."}})
            snapshot = (current_link.snapshot if current_link and current_link.deleted_at is None
                        else InformeService._snapshot(informe.tipo, entity_id, informe.memoria))
            link = links.get(entity_id)
            if link is None:
                db.session.add(cls(informe_id=informe.id, **{key: entity_id}, snapshot=snapshot, created_by=user_id))
                action = "vincular"
            elif link.deleted_at is not None:
                link.restore()
                link.snapshot = snapshot
                link.mark_updated(user_id)
                action = "vincular"
            else:
                link.snapshot = snapshot
                continue
            if not inicial:
                AuditoriaService.registrar_evento_relacion("informe", informe.id, "vinculos_ids", action, {"id": entity_id, "nombre": snapshot.get("nombre_apellido") or snapshot.get("nombre_proyecto")}, user_id)
        for entity_id, link in links.items():
            if entity_id not in desired and link.deleted_at is None:
                link.soft_delete(user_id)
                if not inicial:
                    AuditoriaService.registrar_evento_relacion("informe", informe.id, "vinculos_ids", "desvincular", {"id": entity_id, "nombre": link.snapshot.get("nombre_apellido") or link.snapshot.get("nombre_proyecto")}, user_id)

    @staticmethod
    def list(tipo, memoria_id=None, page=1, per_page=9):
        InformeService._tipo(tipo)
        if type(page) is not int or page < 1 or type(per_page) is not int or not 1 <= per_page <= 9:
            raise ValidationError("Revise la paginación solicitada.")
        query = Informe.query.filter_by(tipo=tipo, grupo_utn_id=InformeService._grupo_id()).filter(Informe.deleted_at.is_(None))
        if memoria_id is not None:
            memoria = InformeService._memoria(memoria_id)
            query = query.filter_by(memoria_id=memoria.id)
        total = query.count()
        items = query.order_by(Informe.fecha_realizacion.desc(), Informe.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return [item.serialize() for item in items], total

    @staticmethod
    def get(tipo, informe_id):
        return InformeService._informe(tipo, informe_id).serialize(detail=True)

    @staticmethod
    def create(tipo, data, user_id):
        InformeService._tipo(tipo)
        if not isinstance(data, dict) or set(data) - {"memoria_id", "fecha_realizacion", "vinculos_ids", *TEXTOS}:
            raise ValidationError("Revise los datos del informe.")
        memoria = InformeService._memoria(data.get("memoria_id"))
        values = {field: InformeService._texto(data.get(field), field) for field in TEXTOS}
        values["fecha_realizacion"] = InformeService._fecha(data.get("fecha_realizacion"))
        ids = InformeService._ids(data.get("vinculos_ids"), tipo)
        informe = Informe(tipo=tipo, memoria_id=memoria.id, grupo_utn_id=memoria.grupo_utn_id, uct_snapshot=InformeService._uct_snapshot(memoria), created_by=user_id, **values)
        db.session.add(informe)
        try:
            db.session.flush()
            InformeService._sincronizar(informe, ids, user_id, inicial=True)
            db.session.commit()
            return informe.serialize(detail=True)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def update(tipo, informe_id, data, user_id):
        informe = InformeService._informe(tipo, informe_id)
        if not isinstance(data, dict) or not data or set(data) - {"fecha_realizacion", "vinculos_ids", *TEXTOS}:
            raise ValidationError("Revise los datos del informe.")
        try:
            changes = {}
            for field in TEXTOS:
                if field not in data:
                    continue
                value = InformeService._texto(data[field], field)
                change = AuditoriaService.construir_cambio(getattr(informe, field), value)
                if change:
                    changes[field] = change
                    setattr(informe, field, value)
            if "fecha_realizacion" in data:
                value = InformeService._fecha(data["fecha_realizacion"])
                change = AuditoriaService.construir_cambio(informe.fecha_realizacion, value)
                if change:
                    changes["fecha_realizacion"] = change
                    informe.fecha_realizacion = value
            if "vinculos_ids" in data:
                ids = InformeService._ids(data["vinculos_ids"], tipo)
                InformeService._sincronizar(informe, ids, user_id)
            if changes:
                AuditoriaService.registrar_cambios("informe", informe.id, changes, user_id)
            if changes or "vinculos_ids" in data:
                informe.mark_updated(user_id)
            db.session.commit()
            return informe.serialize(detail=True)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def delete(tipo, informe_id, user_id):
        informe = InformeService._informe(tipo, informe_id)
        if tipo == "pid":
            from modules.informes.services.cierre_proyecto import tiene_informe_de_cierre
            for link in informe.proyectos:
                if link.deleted_at is None:
                    proyecto = db.session.get(ProyectoInvestigacion, link.proyecto_id)
                    if proyecto and proyecto.deleted_at and proyecto.fecha_fin and proyecto.fecha_fin <= date.today() and informe.memoria.periodo_inicio <= proyecto.fecha_fin <= informe.memoria.periodo_fin and not tiene_informe_de_cierre(proyecto.id, proyecto.fecha_fin, informe.id, grupo_utn_id=proyecto.grupo_utn_id):
                        raise ConflictError("No puede eliminar un informe PID requerido para el cierre de un proyecto.")
        informe.soft_delete(user_id)
        db.session.commit()
        return {"message": "Informe eliminado con éxito"}

    @staticmethod
    def history(tipo, informe_id):
        informe = InformeService._informe(tipo, informe_id)
        return AuditoriaService.obtener_historial_entidad("informe", informe.id)
