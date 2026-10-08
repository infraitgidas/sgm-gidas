import re
import unittest
from unittest.mock import patch

from app import create_app


class IdorBolaModulesTestCase(unittest.TestCase):

    def setUp(self):
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    @staticmethod
    def _materialize_path(rule: str) -> str:
        path = re.sub(r"<int:[^>]+>", "1", rule)
        return re.sub(r"<string:rol>", "investigador", path)

    def _mutation_rules(self):
        prefixes = (
            "/api/v1/personal",
            "/api/v1/grupo",
            "/api/v1/recursos",
            "/api/v1/produccion",
            "/api/v1/proyectos",
            "/api/v1/transferencia",
            "/api/v1/catalogos",
            "/api/v1/memorias",
            "/api/v1/dashboards",
            "/api/v1/search",
        )
        mutation_methods = {"POST", "PUT", "PATCH", "DELETE"}
        rules = []
        for rule in self.app.url_map.iter_rules():
            if not rule.rule.startswith(prefixes):
                continue
            for method in sorted(rule.methods & mutation_methods):
                rules.append((method, self._materialize_path(rule.rule)))
        return sorted(rules)

    def _privileged_read_rules(self):
        return sorted(
            self._materialize_path(rule.rule)
            for rule in self.app.url_map.iter_rules()
            if "GET" in rule.methods and "/exportar-" in rule.rule
        )

    def test_lectura_no_puede_ejecutar_ninguna_mutacion(self):
        rules = self._mutation_rules()
        self.assertGreater(len(rules), 0)

        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "91", "rol": "LECTURA"},
        ):
            for method, path in rules:
                with self.subTest(method=method, path=path):
                    response = self.client.open(
                        path,
                        method=method,
                        json={},
                        headers={"Authorization": "Bearer fake-token"},
                    )
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(
                        response.get_json()["error"]["code"],
                        "FORBIDDEN",
                    )

    def test_lectura_no_puede_ejecutar_exportaciones_privilegiadas(self):
        rules = self._privileged_read_rules()
        self.assertGreater(len(rules), 0)

        with patch(
            "modules.shared.services.middleware.AuthService.verify_token",
            return_value={"sub": "91", "rol": "LECTURA"},
        ):
            for path in rules:
                with self.subTest(path=path):
                    response = self.client.get(
                        path,
                        headers={"Authorization": "Bearer fake-token"},
                    )
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(
                        response.get_json()["error"]["code"],
                        "FORBIDDEN",
                    )


if __name__ == "__main__":
    unittest.main()
