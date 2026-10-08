"""Comprueba recuperacion real de cada modulo de la busqueda global."""

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.grupo.models.directivos import Directivo
from modules.grupo.models.visita_grupo import VisitaAcademica
from modules.personal.models.personal import Becario, Investigador, Personal
from modules.personal.models.tipo_personal import TipoPersonal
from modules.produccion.models.actividad_docencia import ActividadDocencia
from modules.produccion.models.articulo_divulgacion import ArticuloDivulgacion
from modules.produccion.models.documentacion_autores import Autor, DocumentacionBibliografica
from modules.produccion.models.registro_patente import RegistrosPropiedad, TipoRegistroPropiedad
from modules.produccion.models.trabajo_reunion import TrabajoReunionCientifica
from modules.produccion.models.trabajo_revista import TrabajosRevistasReferato
from modules.proyectos.models.participacion_relevante import ParticipacionRelevante
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion, TipoProyecto
from modules.recursos.models.becas import Beca
from modules.recursos.models.equipamiento import Equipamiento
from modules.recursos.models.movimiento_financiero import MovimientoFinanciero
from modules.search.services.search_service import SearchService
from modules.transferencia.models.transferencia_socio import TipoContrato, TransferenciaSocioProductiva


@dataclass(frozen=True)
class Probe:
    modulo: str
    tipo: str
    modelo: type
    texto: Callable[[object], str]
    url: str


PROBES = (
    Probe("personal", "Persona", Personal, lambda x: x.nombre_apellido, "/personal/"),
    Probe("becarios", "Becario", Becario, lambda x: x.nombre_apellido, "/becarios/"),
    Probe("becas", "Beca", Beca, lambda x: x.nombre_beca, "/becas/"),
    Probe("investigadores", "Investigador", Investigador, lambda x: x.nombre_apellido, "/investigadores/"),
    Probe("docencia", "Actividad de Docencia", ActividadDocencia, lambda x: x.curso, "/actividades-docencia/"),
    Probe("proyectos", "Proyecto de Investigación", ProyectoInvestigacion, lambda x: x.nombre_proyecto, "/proyectos/"),
    Probe("tipos-proyecto", "Tipo de Proyecto", TipoProyecto, lambda x: x.nombre, "/tipos-proyecto/"),
    Probe("equipamiento", "Equipamiento", Equipamiento, lambda x: x.denominacion, "/equipamiento/"),
    Probe("documentacion", "Documentación", DocumentacionBibliografica, lambda x: x.titulo, "/documentacion-bibliografica/"),
    Probe("autores", "Autor", Autor, lambda x: x.nombre_apellido, "/autores/"),
    Probe("movimientos", "Movimiento financiero", MovimientoFinanciero, lambda x: x.categoria_erogacion.nombre if x.categoria_erogacion else x.fuente_financiamiento.nombre, "/movimientos/"),
    Probe("financiamiento", "Fuente de Financiamiento", FuenteFinanciamiento, lambda x: x.nombre, "/fuentes-financiamiento/"),
    Probe("participaciones", "Participación Relevante", ParticipacionRelevante, lambda x: x.nombre_evento, "/participaciones-relevantes/"),
    Probe("registros", "Registro de Propiedad", RegistrosPropiedad, lambda x: x.nombre_articulo, "/registros-propiedad/"),
    Probe("tipos-registro", "Tipo Registro Propiedad", TipoRegistroPropiedad, lambda x: x.nombre, "/tipos-registro-propiedad/"),
    Probe("transferencias", "Transferencia Socio Productiva", TransferenciaSocioProductiva, lambda x: x.descripcion_actividad, "/transferencias/"),
    Probe("tipos-contrato", "Tipo de Contrato", TipoContrato, lambda x: x.nombre, "/tipos-contrato/"),
    Probe("tipos-personal", "Tipo Personal", TipoPersonal, lambda x: x.nombre, "/tipos-personal/"),
    Probe("reuniones", "Trabajo en Reunión Científica", TrabajoReunionCientifica, lambda x: x.titulo_trabajo, "/trabajos-reunion/"),
    Probe("revistas", "Trabajo en Revista con Referato", TrabajosRevistasReferato, lambda x: x.titulo_trabajo, "/trabajos-revistas/"),
    Probe("directivos", "Directivo", Directivo, lambda x: x.nombre_apellido, "/directivos/"),
    Probe("articulos", "Artículo de Divulgación", ArticuloDivulgacion, lambda x: x.titulo, "/articulos-divulgacion/"),
    Probe("visitas", "Visita Académica", VisitaAcademica, lambda x: x.razon, "/visitas-academicas/"),
)


def verificar(probe: Probe) -> tuple[bool, str]:
    query = probe.modelo.query
    if hasattr(probe.modelo, "deleted_at"):
        query = query.filter(probe.modelo.deleted_at.is_(None))
    registros = query.order_by(probe.modelo.id.asc()).limit(25).all()
    if not registros:
        return False, "sin datos activos"

    for registro in registros:
        texto = str(probe.texto(registro) or "").strip()
        if len(texto) < 2:
            continue
        resultados = SearchService.search(texto, max_scan_per_model=300)
        if any(
            item.get("tipo") == probe.tipo
            and item.get("id") == registro.id
            and str(item.get("url", "")).startswith(probe.url)
            for item in resultados
        ):
            return True, f"id={registro.id}"
    return False, "no se recupero un registro representativo"


def main() -> int:
    from app import app

    fallos = []
    with app.app_context():
        for probe in PROBES:
            ok, detalle = verificar(probe)
            print(f"[{'OK' if ok else 'ERROR'}] {probe.modulo}: {detalle}")
            if not ok:
                fallos.append(probe.modulo)
    if fallos:
        print("Modulos pendientes: " + ", ".join(fallos))
        return 1
    print(f"Recuperacion validada para {len(PROBES)} modulos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
