import unittest

from tools.validate_production_topology import validate_config


def valid_config():
    return {
        "services": {
            "backend": {
                "environment": {
                    "DATABASE_URL": "postgresql://gidas_app:secret@db/gidas_db"
                },
                "expose": ["5000"],
            },
            "frontend": {"expose": ["8080"]},
            "db": {},
            "redis": {"expose": ["6379"]},
            "migrate": {
                "environment": {
                    "DATABASE_URL": "postgresql://gidas_admin:secret@db/gidas_db",
                    "POSTGRES_APP_USER": "gidas_app",
                }
            },
            "nginx": {
                "ports": [
                    {
                        "host_ip": "127.0.0.1",
                        "published": "8080",
                        "target": 8080,
                    }
                ]
            },
        }
    }


class ProductionTopologyTestCase(unittest.TestCase):

    def test_acepta_proxy_como_unico_servicio_publicado(self):
        self.assertEqual(validate_config(valid_config()), [])

    def test_rechaza_puerto_publicado_en_servicio_privado(self):
        for service_name in ("backend", "frontend", "db", "redis"):
            with self.subTest(service_name=service_name):
                config = valid_config()
                config["services"][service_name]["ports"] = [5000]

                errors = validate_config(config)

                self.assertTrue(
                    any(service_name in error for error in errors),
                    errors,
                )

    def test_rechaza_publicacion_de_servicio_no_autorizado(self):
        config = valid_config()
        config["services"]["migrate"]["ports"] = [9000]

        errors = validate_config(config)

        self.assertIn("migrate publica puertos sin estar autorizado", errors)

    def test_rechaza_backend_con_usuario_distinto_del_runtime(self):
        config = valid_config()
        config["services"]["backend"]["environment"]["DATABASE_URL"] = (
            "postgresql://usuario_legacy:secret@db/gidas_db"
        )

        errors = validate_config(config)

        self.assertIn("DATABASE_URL del backend no usa POSTGRES_APP_USER", errors)

    def test_rechaza_usuario_compartido_entre_runtime_y_migraciones(self):
        config = valid_config()
        config["services"]["migrate"]["environment"]["DATABASE_URL"] = (
            "postgresql://gidas_app:secret@db/gidas_db"
        )

        errors = validate_config(config)

        self.assertIn("Runtime y migraciones no deben usar el mismo usuario", errors)

    def test_rechaza_proxy_sin_puerto_publicado(self):
        config = valid_config()
        config["services"]["nginx"]["ports"] = []

        errors = validate_config(config)

        self.assertIn("nginx debe publicar exactamente un puerto", errors)

    def test_rechaza_binding_no_soportado(self):
        config = valid_config()
        config["services"]["nginx"]["ports"] = [
            {"host_ip": "no-es-una-ip", "published": "8080", "target": 8080}
        ]

        errors = validate_config(config)

        self.assertIn("NGINX_BIND_ADDRESS no es un binding soportado", errors)

    def test_rechaza_binding_publico_de_nginx(self):
        for host_ip in ("0.0.0.0", "192.168.1.50", "::"):
            with self.subTest(host_ip=host_ip):
                config = valid_config()
                config["services"]["nginx"]["ports"][0]["host_ip"] = host_ip

                errors = validate_config(config)

                self.assertIn(
                    "nginx debe publicar solo en loopback para el origen local",
                    errors,
                )

    def test_rechaza_publicacion_sin_host_ip_explicito(self):
        config = valid_config()
        del config["services"]["nginx"]["ports"][0]["host_ip"]

        errors = validate_config(config)

        self.assertIn(
            "nginx debe publicar solo en loopback para el origen local", errors
        )


if __name__ == "__main__":
    unittest.main()
