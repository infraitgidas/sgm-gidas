"""Guardado atómico de datos y diferencias relacionales de proyectos."""
from datetime import date

from extension import db
from modules.personal.models.personal import Investigador, Becario
from modules.proyectos.models.proyecto_investigacion import (
    ProyectoInvestigacion, InvestigadorProyecto, BecarioProyecto,
)
from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService
from modules.shared.exceptions import ValidationError
from modules.shared.services.auditoria_service import AuditoriaService


class ProyectoGuardadoService:
    @staticmethod
    def guardar(data, user_id, proyecto_id=None):
        if not isinstance(data, dict) or not data:
            raise ValidationError("El body es obligatorio")
        try:
            if proyecto_id is not None:
                # Serializa cambios del agregado incluso entre peticiones concurrentes.
                proyecto = ProyectoInvestigacionService._get_proyecto_activo_or_404(
                    proyecto_id
                )
                ProyectoInvestigacionService._validar_proyecto_abierto(proyecto)
            campos = {k: v for k, v in data.items() if k not in (
                "investigadores_ids", "becarios_ids", "coordinador_id"
            )}
            if proyecto_id is None:
                result = ProyectoInvestigacionService.create(campos, user_id, commit=False)
                proyecto = db.session.get(ProyectoInvestigacion, result["id"])
            elif campos:
                ProyectoInvestigacionService.update(proyecto_id, campos, user_id, commit=False)
            for key, model, relation, fk, attr in (
                ("investigadores_ids", Investigador, InvestigadorProyecto, "id_investigador", "participaciones_investigador"),
                ("becarios_ids", Becario, BecarioProyecto, "id_becario", "participaciones_becario"),
            ):
                if key not in data and not (model is Investigador and "coordinador_id" in data):
                    continue
                actuales = {getattr(p, fk): p for p in getattr(proyecto, attr) if p.deleted_at is None}
                ids = data.get(key, list(actuales))
                if not isinstance(ids, list) or any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
                    raise ValidationError("Seleccione integrantes válidos e intente nuevamente.", details={"fields": {key: "Complete las selecciones sin duplicados."}})
                coordinator = None
                if model is Investigador:
                    previo = next((i for i, p in actuales.items() if p.es_coordinador), None)
                    coordinator = data.get("coordinador_id", previo)
                    if coordinator is not None and (type(coordinator) is not int or coordinator not in ids):
                        raise ValidationError("Seleccione un coordinador entre los investigadores elegidos.", details={"fields": {"coordinador_id": "Seleccione un investigador del proyecto."}})
                    if ids and coordinator is None:
                        raise ValidationError("Seleccione un coordinador.", details={"fields": {"coordinador_id": "Seleccione un coordinador."}})
                for i in ids:
                    persona = db.session.get(model, i)
                    # Permite conservar integrantes históricos, nunca nuevas asignaciones inactivas.
                    nueva_asignacion = i not in actuales or (model is Investigador and i == coordinator and not actuales[i].es_coordinador)
                    if not persona or (nueva_asignacion and (persona.deleted_at is not None or not persona.activo)):
                        raise ValidationError("Seleccione un integrante activo e intente nuevamente.", details={"fields": {"coordinador_id" if model is Investigador and i == coordinator else key: "Seleccione un integrante activo disponible."}})
                changed = False
                for i, p in actuales.items():
                    if i not in ids:
                        p.fecha_fin = max(date.today(), p.fecha_inicio)
                        p.soft_delete(user_id)
                        if proyecto_id is not None:
                            persona = db.session.get(model, i)
                            ProyectoGuardadoService._evento(
                                proyecto.id,
                                key,
                                "desvincular",
                                persona,
                                user_id,
                            )
                        changed = True
                for i in ids:
                    if i not in actuales:
                        persona = db.session.get(model, i)
                        values = {fk: i, "id_proyecto": proyecto.id, "fecha_inicio": proyecto.fecha_inicio, "created_by": user_id}
                        if proyecto_id is None and proyecto.fecha_fin and proyecto.fecha_fin <= date.today():
                            values["fecha_fin"] = proyecto.fecha_fin
                        if model is Investigador:
                            values["es_coordinador"] = i == coordinator
                        db.session.add(relation(**values))
                        if proyecto_id is not None:
                            ProyectoGuardadoService._evento(
                                proyecto.id,
                                key,
                                "vincular",
                                persona,
                                user_id,
                            )
                        changed = True
                    elif model is Investigador and actuales[i].es_coordinador != (i == coordinator):
                        actuales[i].es_coordinador = i == coordinator
                        actuales[i].mark_updated(user_id)
                        changed = True
                if proyecto_id is not None and model is Investigador and previo != coordinator:
                    AuditoriaService.registrar_cambios("proyecto_investigacion", proyecto.id, {
                        "coordinador_id": AuditoriaService.construir_cambio(previo, coordinator)
                    }, user_id)
                    changed = True
                if proyecto_id is not None and changed:
                    proyecto.mark_updated(user_id)
            db.session.commit()
            db.session.expire(proyecto)
            return proyecto.serialize()
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def _evento(proyecto_id, relacion, accion, persona, user_id):
        AuditoriaService.registrar_evento_relacion(
            "proyecto_investigacion", proyecto_id, relacion, accion,
            {
                "id": persona.id,
                "nombre_apellido": persona.nombre_apellido,
            },
            user_id,
        )
