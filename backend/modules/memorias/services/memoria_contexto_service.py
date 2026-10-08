from modules.grupo.models.directivos import DirectivoGrupo
from modules.grupo.models.programa_actividades import PlanificacionGrupo
from modules.memorias.services.memoria_periodo_service import (
    estuvo_activo_en_periodo_memoria,
    fin_vigencia,
    relacion_vigente_en_memoria,
)


def snapshot_contexto_institucional(version):
    from modules.informes.models.informe import Informe
    memoria = version.memoria
    grupo = memoria.grupo_utn
    datos_grupo = {campo: getattr(grupo, campo) for campo in (
        "id", "nombre_unidad_academica", "nombre_sigla_grupo", "mail", "objetivo_desarrollo",
    )}
    directivos = []
    for participacion in DirectivoGrupo.query.filter_by(id_grupo_utn=grupo.id).all():
        if not estuvo_activo_en_periodo_memoria(version, participacion.fecha_inicio, fin_vigencia(participacion)):
            continue
        if participacion.directivo is None or not relacion_vigente_en_memoria(version, participacion.directivo):
            continue
        directivos.append({
            "nombre_apellido": participacion.directivo.nombre_apellido,
            "cargo": participacion.cargo.nombre if participacion.cargo else None,
            "fecha_inicio": participacion.fecha_inicio.isoformat(),
            "fecha_fin": participacion.fecha_fin.isoformat() if participacion.fecha_fin else None,
        })
    plan = PlanificacionGrupo.query.filter_by(
        grupo_id=grupo.id, anio=memoria.periodo_fin.year + 1, deleted_at=None,
    ).order_by(PlanificacionGrupo.id.desc()).first()
    informes = Informe.query.filter_by(memoria_id=memoria.id, grupo_utn_id=grupo.id, deleted_at=None).order_by(
        Informe.fecha_realizacion, Informe.id,
    ).all()
    logros = {}
    for informe in informes:
        if informe.tipo == "pid":
            for vinculo in informe.proyectos:
                if vinculo.deleted_at is None:
                    logros.setdefault(str(vinculo.proyecto_id), []).append(informe.resultados)
    return {
        "_schema_version": 2,
        "grupo": datos_grupo,
        "directivos": directivos,
        "programa_actividades": plan.descripcion if plan else None,
        "anio_programa": memoria.periodo_fin.year + 1,
        "logros_proyectos": {key: "\n\n".join(values) for key, values in logros.items()},
    }
