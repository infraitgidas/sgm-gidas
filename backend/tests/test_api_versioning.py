import unittest

from flask import Blueprint, Flask

from app import create_app
from modules import blueprints

from modules.shared.routes.status import health_bp
from modules.shared.routes.versioning import (
    API_VERSION,
    API_VERSION_HEADER,
    API_V1_PREFIX,
    VERSIONED_PREFIXES,
    register_api_version_header,
    register_blueprints,
)


class ApiVersioningTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True)
        register_blueprints(self.app, [health_bp])
        register_api_version_header(self.app)
        self.client = self.app.test_client()

    def test_registra_solo_ruta_versionada(self):
        rules = {rule.rule for rule in self.app.url_map.iter_rules()}

        self.assertNotIn("/health", rules)
        self.assertIn(f"{API_V1_PREFIX}/health", rules)

    def test_endpoint_versionado_responde_con_header_api_version(self):
        response = self.client.get(f"{API_V1_PREFIX}/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers[API_VERSION_HEADER], API_VERSION)
        self.assertEqual(response.get_json()["data"], {"status": "ok"})

    def test_endpoint_legacy_no_existe(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(API_VERSION_HEADER, response.headers)

    def test_nombre_endpoint_versionado_usa_namespace_v1(self):
        endpoints = {rule.endpoint for rule in self.app.url_map.iter_rules()}

        self.assertNotIn("health.health", endpoints)
        self.assertIn("v1_health.health", endpoints)

    def test_preserva_prefijo_original_del_blueprint(self):
        app = Flask(__name__)
        items_bp = Blueprint("items", __name__, url_prefix="/items")

        @items_bp.get("/")
        def listar_items():
            return []

        register_blueprints(app, [items_bp])

        rules = {rule.rule for rule in app.url_map.iter_rules()}
        self.assertNotIn("/items/", rules)
        self.assertIn(f"{API_V1_PREFIX}/items/", rules)

    def test_usa_nomenclatura_canonica_para_catalogos(self):
        app = Flask(__name__)
        fuente_bp = Blueprint(
            "fuente_financiamiento",
            __name__,
            url_prefix="/fuente-financiamiento",
        )

        @fuente_bp.get("/")
        def listar_fuentes():
            return []

        register_blueprints(app, [fuente_bp])

        rules = {rule.rule for rule in app.url_map.iter_rules()}
        self.assertNotIn("/fuente-financiamiento/", rules)
        self.assertIn("/api/v1/catalogos/fuente-financiamiento/", rules)
        self.assertNotIn("/api/v1/fuente-financiamiento/", rules)

    def test_app_expone_login_y_endpoint_protegido_en_v1(self):
        app = create_app()
        rules = {rule.rule for rule in app.url_map.iter_rules()}

        self.assertIn(f"{API_V1_PREFIX}/auth/login", rules)
        self.assertIn(f"{API_V1_PREFIX}/auth/logout", rules)
        self.assertIn(f"{API_V1_PREFIX}/auth/perfil", rules)

    def test_app_expone_nomenclatura_v1_por_dominio(self):
        app = create_app()
        rules = {rule.rule for rule in app.url_map.iter_rules()}

        self.assertIn("/api/v1/catalogos/fuente-financiamiento/", rules)
        self.assertIn("/api/v1/personal/investigadores/", rules)
        self.assertIn("/api/v1/recursos/becas/", rules)
        self.assertIn("/api/v1/produccion/articulos-divulgacion/", rules)
        self.assertIn("/api/v1/proyectos", rules)
        self.assertIn("/api/v1/transferencia/transferencias", rules)
        self.assertIn("/api/v1/grupo/cargos/", rules)
        self.assertIn("/api/v1/grupo/tipos-visita/", rules)

    def test_app_no_expone_rutas_legacy(self):
        app = create_app()
        rules = {rule.rule for rule in app.url_map.iter_rules()}

        self.assertNotIn("/auth/login", rules)
        self.assertNotIn("/fuente-financiamiento/", rules)
        self.assertNotIn("/investigadores/", rules)
        self.assertNotIn("/becas/", rules)
        self.assertNotIn("/proyectos", rules)

    def test_todos_los_blueprints_conocidos_tienen_prefijo_canonico(self):
        expected_blueprints = {blueprint.name for blueprint in blueprints}

        self.assertEqual(set(VERSIONED_PREFIXES), expected_blueprints)


if __name__ == "__main__":
    unittest.main()
