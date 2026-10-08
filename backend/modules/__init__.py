"""Registro diferido de blueprints del monolito modular backend."""


def get_blueprints():
    from modules.auth.routes.auth_rutas import auth_bp
    from modules.catalogos.routes.categoria_utn_routes import categoria_utn_bp
    from modules.catalogos.routes.fuente_financiamiento_rutas import (
        fuente_financiamiento_bp,
    )
    from modules.dashboard.routes.dashboard_rutas import dashboard_bp
    from modules.grupo.routes.cargos_rutas import cargo_bp
    from modules.grupo.routes.directivo_rutas import directivo_bp
    from modules.grupo.routes.grupo_rutas import grupo_utn_bp
    from modules.grupo.routes.programa_actividades_rutas import (
        planificacion_grupo_bp,
    )
    from modules.grupo.routes.programa_incentivos_rutas import (
        programa_incentivos_bp,
    )
    from modules.grupo.routes.visita_rutas import visita_academica_bp
    from modules.grupo.routes.tipo_visita_rutas import tipo_visita_bp
    from modules.memorias.routes.memorias_rutas import memoria_bp
    from modules.informes.routes.informe_rutas import informe_bp
    from modules.personal.routes.becario_rutas import becario_bp
    from modules.personal.routes.investigador_rutas import investigador_bp
    from modules.personal.routes.personal_completo_ruta import personal_completo_bp
    from modules.personal.routes.personal_rutas import personal_bp
    from modules.personal.routes.tipo_dedicacion_rutas import tipo_dedicacion_bp
    from modules.personal.routes.tipo_formacion_rutas import tipo_formacion_becario_bp
    from modules.personal.routes.tipo_personal_rutas import tipo_personal_bp
    from modules.produccion.routes.actividad_docencia_rutas import (
        actividad_docencia_bp,
    )
    from modules.produccion.routes.articulo_divulgacion_rutas import (
        articulo_divulgacion_bp,
    )
    from modules.produccion.routes.autores_rutas import autor_bp
    from modules.produccion.routes.distinciones_rutas import distincion_recibida_bp
    from modules.produccion.routes.documentacion_rutas import (
        documentacion_bibliografica_bp,
    )
    from modules.produccion.routes.grado_academico_rutas import grado_academico_bp
    from modules.produccion.routes.registro_propiedad_rutas import (
        registros_propiedad_bp,
    )
    from modules.produccion.routes.rol_actividad_rutas import rol_actividad_bp
    from modules.produccion.routes.tipo_registro_rutas import (
        tipo_registro_propiedad_bp,
    )
    from modules.produccion.routes.tipo_reunion_rutas import tipo_reunion_bp
    from modules.produccion.routes.tipo_revista_rutas import tipo_revista_bp
    from modules.produccion.routes.trabajo_reunion_rutas import (
        trabajo_reunion_cientifica_bp,
    )
    from modules.produccion.routes.trabajo_revista_rutas import (
        trabajos_revistas_referato_bp,
    )
    from modules.proyectos.routes.participacion_relevante_rutas import (
        participacion_relevante_bp,
    )
    from modules.proyectos.routes.proyecto_investigacion_rutas import (
        proyecto_investigacion_bp,
    )
    from modules.proyectos.routes.tipo_proyecto_rutas import tipo_proyecto_bp
    from modules.recursos.routes.becas_rutas import beca_bp
    from modules.recursos.routes.equipamiento_rutas import equipamiento_bp
    from modules.recursos.routes.movimiento_financiero_rutas import movimiento_financiero_bp
    from modules.search.routes.search_rutas import search_bp
    from modules.shared.routes.status import health_bp
    from modules.shared.routes.form_draft_routes import form_draft_bp
    from modules.transferencia.routes.adoptante_rutas import adoptante_bp
    from modules.transferencia.routes.tipo_contrato_rutas import tipo_contrato_bp
    from modules.transferencia.routes.transferencia_socio_rutas import (
        transferencia_socio_productiva_bp,
    )

    return [
        health_bp,
        form_draft_bp,
        actividad_docencia_bp,
        articulo_divulgacion_bp,
        adoptante_bp,
        auth_bp,
        autor_bp,
        becario_bp,
        beca_bp,
        categoria_utn_bp,
        cargo_bp,
        dashboard_bp,
        distincion_recibida_bp,
        directivo_bp,
        documentacion_bibliografica_bp,
        equipamiento_bp,
        movimiento_financiero_bp,
        fuente_financiamiento_bp,
        grupo_utn_bp,
        grado_academico_bp,
        investigador_bp,
        participacion_relevante_bp,
        personal_bp,
        personal_completo_bp,
        planificacion_grupo_bp,
        proyecto_investigacion_bp,
        programa_incentivos_bp,
        registros_propiedad_bp,
        rol_actividad_bp,
        search_bp,
        tipo_contrato_bp,
        tipo_dedicacion_bp,
        tipo_formacion_becario_bp,
        tipo_personal_bp,
        tipo_registro_propiedad_bp,
        tipo_proyecto_bp,
        trabajo_reunion_cientifica_bp,
        trabajos_revistas_referato_bp,
        transferencia_socio_productiva_bp,
        visita_academica_bp,
        tipo_visita_bp,
        tipo_reunion_bp,
        tipo_revista_bp,
        memoria_bp,
        informe_bp,
    ]


class LazyBlueprints:
    def __iter__(self):
        return iter(get_blueprints())


blueprints = LazyBlueprints()
