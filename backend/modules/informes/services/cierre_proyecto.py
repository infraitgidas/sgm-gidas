"""Condicion compartida para el cierre manual y por vencimiento de un PID."""
from sqlalchemy import and_, exists, select

from extension import db
from modules.informes.models.informe import Informe, InformeProyecto
from modules.memorias.models.memorias import Memoria
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion


def informe_de_cierre_predicate(proyecto_id, fecha_fin, grupo_utn_id, excluir_informe_id=None):
    conditions = [
        InformeProyecto.proyecto_id == proyecto_id,
        InformeProyecto.deleted_at.is_(None),
        Informe.deleted_at.is_(None),
        Informe.tipo == "pid",
        Memoria.deleted_at.is_(None),
        Memoria.periodo_inicio <= fecha_fin,
        Memoria.periodo_fin >= fecha_fin,
        Informe.grupo_utn_id == Memoria.grupo_utn_id,
        Informe.grupo_utn_id == grupo_utn_id,
    ]
    if excluir_informe_id is not None:
        conditions.append(Informe.id != excluir_informe_id)
    return exists(select(InformeProyecto.id).join(
        Informe, Informe.id == InformeProyecto.informe_id
    ).join(
        Memoria, Memoria.id == Informe.memoria_id
    ).where(and_(*conditions)).correlate_except(InformeProyecto, Informe, Memoria))


def tiene_informe_de_cierre(proyecto_id, fecha_fin, excluir_informe_id=None, grupo_utn_id=None):
    if proyecto_id is None or fecha_fin is None:
        return False
    if grupo_utn_id is None:
        grupo_utn_id = db.session.execute(select(ProyectoInvestigacion.grupo_utn_id).where(ProyectoInvestigacion.id == proyecto_id)).scalar()
    if grupo_utn_id is None:
        return False
    return bool(db.session.execute(select(informe_de_cierre_predicate(proyecto_id, fecha_fin, grupo_utn_id, excluir_informe_id))).scalar())
