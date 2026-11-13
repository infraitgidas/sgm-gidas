import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class HttpsDeploymentTemplateTestCase(unittest.TestCase):

    def test_proxy_tls_externo_es_alternativo_al_cloudflare_tunnel(self):
        template = (
            REPOSITORY_ROOT / "nginx" / "gidas.external.conf.example"
        ).read_text(encoding="utf-8")

        self.assertIn("no se instala ni se utiliza este proxy externo", template)
        self.assertIn("listen 443 ssl;", template)
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", template)
        self.assertIn("return 301 https://$host$request_uri;", template)
        self.assertIn("proxy_pass http://127.0.0.1:8080;", template)
        self.assertIn("# add_header Strict-Transport-Security", template)
        self.assertNotIn("[IP_ADDRESS]", template)

    def test_proxy_interno_preserva_el_esquema_https_validado(self):
        internal_proxy = (REPOSITORY_ROOT / "nginx" / "default.conf").read_text(
            encoding="utf-8"
        )

        self.assertIn("map $http_x_forwarded_proto $gidas_forwarded_proto", internal_proxy)
        self.assertIn("https https;", internal_proxy)
        self.assertNotIn("proxy_set_header X-Forwarded-Proto $scheme;", internal_proxy)
        # 9 = las 7 locations originales mas las 2 que agrega el portal bajo
        # /sgm-gidas/, todas con la variable validada y ninguna con $scheme.
        self.assertEqual(
            internal_proxy.count(
                "proxy_set_header X-Forwarded-Proto $gidas_forwarded_proto;"
            ),
            9,
        )
        self.assertIn("proxy_connect_timeout 10s;", internal_proxy)
        self.assertIn("proxy_send_timeout 120s;", internal_proxy)
        self.assertIn("proxy_read_timeout 120s;", internal_proxy)

    def test_ejemplo_productivo_recomienda_binding_a_loopback(self):
        environment_example = (REPOSITORY_ROOT / ".env.production.example").read_text(
            encoding="utf-8"
        )

        self.assertIn("NGINX_BIND_ADDRESS=127.0.0.1", environment_example)
        self.assertIn("# GIDAS_SERVER_NAME=", environment_example)
        self.assertIn("# GIDAS_TLS_CERTIFICATE_PATH=", environment_example)
        self.assertIn("# GIDAS_TLS_CERTIFICATE_KEY_PATH=", environment_example)

    def test_frontend_genera_archivos_gzip_para_gzip_static(self):
        dockerfile = (REPOSITORY_ROOT / "frontend" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        frontend_nginx = (REPOSITORY_ROOT / "frontend" / "nginx.conf").read_text(
            encoding="utf-8"
        )

        self.assertIn("npm run build:production", dockerfile)
        self.assertIn("gzip -9 -k", dockerfile)
        self.assertIn("gzip_static on;", frontend_nginx)


if __name__ == "__main__":
    unittest.main()
