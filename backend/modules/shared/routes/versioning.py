API_VERSION = "v1"
API_VERSION_HEADER = "API-Version"
API_V1_PREFIX = "/api/v1"

VERSIONED_PREFIXES = {
    "actividad_docencia": "/api/v1/produccion/actividades-docencia",
    "adoptante": "/api/v1/transferencia/adoptantes",
    "articulo_divulgacion_bp": "/api/v1/produccion/articulos-divulgacion",
    "auth": "/api/v1/auth",
    "autor": "/api/v1/produccion/autores",
    "beca": "/api/v1/recursos/becas",
    "becario": "/api/v1/personal/becarios",
    "cargo": "/api/v1/grupo/cargos",
    "categoria_utn": "/api/v1/catalogos/categoria-utn",
    "dashboard": "/api/v1/dashboards",
    "directivo": "/api/v1/grupo/directivos",
    "distincion_recibida": "/api/v1/produccion/distinciones",
    "documentacion_bibliografica": "/api/v1/produccion/documentacion-bibliografica",
    "equipamiento": "/api/v1/recursos/equipamiento",
    "fuente_financiamiento": "/api/v1/catalogos/fuente-financiamiento",
    "form_draft": "/api/v1/borradores",
    "grado_academico": "/api/v1/produccion/grado-academico",
    "grupo_utn": "/api/v1/grupo/grupo-utn",
    "health": "/api/v1",
    "investigador": "/api/v1/personal/investigadores",
    "informe": "/api/v1/informes",
    "memoria": "/api/v1/memorias",
    "movimiento_financiero": "/api/v1/recursos/movimientos",
    "participacion_relevante": "/api/v1/proyectos/participaciones-relevantes",
    "personal": "/api/v1/personal",
    "personal_completo": "/api/v1/personal/all",
    "planificacion_grupo": "/api/v1/grupo/planificaciones",
    "programa_incentivos": "/api/v1/grupo/programas-incentivos",
    "proyecto_investigacion": "/api/v1/proyectos",
    "registros_propiedad": "/api/v1/produccion/registros-propiedad",
    "rol_actividad": "/api/v1/produccion",
    "search": "/api/v1",
    "tipo_contrato": "/api/v1/transferencia/tipo-contrato",
    "tipo_dedicacion": "/api/v1/personal/tipo-dedicacion",
    "tipo_formacion": "/api/v1/personal/tipo-formacion",
    "tipo_personal": "/api/v1/personal/tipo-personal",
    "tipo_proyecto": "/api/v1/proyectos/tipos-proyecto",
    "tipo_registro_propiedad": "/api/v1/produccion/tipo-registro-propiedad",
    "tipo_reunion": "/api/v1/produccion/tipos-reunion-cientifica",
    "tipo_revista": "/api/v1/produccion/tipos-revista",
    "tipo_visita": "/api/v1/grupo/tipos-visita",
    "trabajo_reunion_cientifica": "/api/v1/produccion/trabajos-reunion-cientifica",
    "trabajos_revistas_referato": "/api/v1/produccion/trabajos-revistas",
    "transferencia_socio_productiva": "/api/v1/transferencia/transferencias",
    "visita_academica": "/api/v1/grupo/visitas-academicas",
}


def register_blueprints(app, blueprints):
    for blueprint in blueprints:
        app.register_blueprint(
            blueprint,
            name=f"{API_VERSION}_{blueprint.name}",
            url_prefix=_versioned_prefix(blueprint),
        )


def register_api_version_header(app):
    @app.after_request
    def add_api_version_header(response):
        if request_path_is_versioned():
            response.headers.setdefault(API_VERSION_HEADER, API_VERSION)
        return response


def request_path_is_versioned():
    from flask import request

    return request.path == API_V1_PREFIX or request.path.startswith(
        f"{API_V1_PREFIX}/"
    )


def _versioned_prefix(blueprint):
    if blueprint.name in VERSIONED_PREFIXES:
        return VERSIONED_PREFIXES[blueprint.name]

    legacy_prefix = getattr(blueprint, "url_prefix", None) or ""
    return f"{API_V1_PREFIX}{legacy_prefix}"
