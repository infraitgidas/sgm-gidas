"""Enriquece las referencias del historial sin alterar los IDs auditados."""
from modules.personal.models.personal import TipoDedicacion, TipoFormacion
from modules.personal.models.tipo_personal import TipoPersonal
from modules.catalogos.models.categoria_utn import CategoriaUtn
from modules.grupo.models.programa_incentivos import ProgramaIncentivos
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.shared.services.auditoria_service import AuditoriaService


CATALOGOS = {
    "tipo_personal_id": (TipoPersonal, "nombre"),
    "tipo_formacion_id": (TipoFormacion, "nombre"),
    "tipo_dedicacion_id": (TipoDedicacion, "nombre"),
    "categoria_utn_id": (CategoriaUtn, "nombre"),
    "programa_incentivos_id": (ProgramaIncentivos, "nombre"),
    "grupo_utn_id": (GrupoInvestigacionUtn, "nombre_sigla_grupo"),
}


def obtener_historial_personal(**kwargs):
    resultado = AuditoriaService.obtener_historial_entidad(**kwargs)
    filas = resultado["data"] if isinstance(resultado, dict) else resultado
    for campo, (modelo, atributo) in CATALOGOS.items():
        afectadas = [fila for fila in filas if fila["campo"] == campo]
        ids = {fila.get(clave) for fila in afectadas for clave in ("valor_anterior", "valor_nuevo")
               if isinstance(fila.get(clave), int) and not isinstance(fila.get(clave), bool)}
        nombres = {item.id: getattr(item, atributo) for item in modelo.query.filter(modelo.id.in_(ids)).all()} if ids else {}
        for fila in afectadas:
            for clave in ("valor_anterior", "valor_nuevo"):
                valor = fila.get(clave)
                fila[f"{clave}_nombre"] = "Sin dato" if valor is None or valor == "" else nombres.get(valor, "Referencia no disponible")
    return resultado
