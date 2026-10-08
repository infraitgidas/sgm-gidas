import unittest
from unittest.mock import patch
from types import SimpleNamespace

from flask import Flask

from modules.auth.controllers.auth_controller import AuthController
from modules.shared.exceptions import AuthenticationError


class AuthCookieContractTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            FRONTEND_URLS=["https://gidas.example.com"],
            REFRESH_COOKIE_NAME="gidas_refresh",
            REFRESH_COOKIE_PATH="/api/v1/auth",
            REFRESH_COOKIE_HTTPONLY=True,
            REFRESH_COOKIE_SECURE=True,
            REFRESH_COOKIE_SAMESITE="Lax",
            REFRESH_TOKEN_EXPIRATION_MINUTES=10080,
        )
        self.app.add_url_rule("/api/v1/auth/login", view_func=AuthController.login, methods=["POST"])
        self.app.add_url_rule("/api/v1/auth/refresh", view_func=AuthController.refresh, methods=["POST"])
        self.app.add_url_rule("/api/v1/auth/logout", view_func=AuthController.logout, methods=["POST"])
        self.app.add_url_rule("/api/v1/auth/cambiar-password", view_func=AuthController.change_password, methods=["POST"])
        self.client = self.app.test_client()

    @patch("modules.auth.controllers.auth_controller.AuthService.login")
    def test_login_identifica_campos_faltantes_sin_llamar_al_service(self, login):
        response = self.client.post("/api/v1/auth/login", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.get_json()["error"]["details"]["fields"]), {"nombre_usuario", "password"})
        login.assert_not_called()

    @patch("modules.auth.controllers.auth_controller.AuthService.login")
    def test_login_separa_credenciales_invalidas_de_fallas_inesperadas(self, login):
        for error, status, code in [
            (AuthenticationError("Verifique su usuario y contraseña."), 401, "AUTH_REQUIRED"),
            (RuntimeError("SELECT password FROM users"), 500, "INTERNAL_ERROR"),
        ]:
            with self.subTest(status=status):
                login.side_effect = error
                response = self.client.post("/api/v1/auth/login", json={"nombre_usuario": "user", "password": "secret"})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.get_json()["error"]["code"], code)
                self.assertNotIn("SELECT", response.get_data(as_text=True))
                self.assertEqual(response.headers["Cache-Control"], "no-store")

    @patch("modules.auth.controllers.auth_controller.AuthService.login")
    def test_login_emite_cookie_segura_y_no_expone_refresh_en_json(self, login):
        login.return_value = {
            "access_token": "access-value",
            "refresh_token": "refresh-value",
            "access_expires_at": "2026-09-10T12:15:00Z",
            "session_expires_at": "2026-09-17T12:00:00Z",
            "session_warning_seconds": 300,
            "user": {"id": 1},
        }

        response = self.client.post(
            "/api/v1/auth/login",
            json={"nombre_usuario": "user", "password": "secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("refresh_token", response.get_json())
        cookie = response.headers["Set-Cookie"]
        self.assertIn("gidas_refresh=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Path=/api/v1/auth", cookie)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    @patch("modules.auth.controllers.auth_controller.AuthService.generate_tokens")
    @patch("modules.auth.controllers.auth_controller.AuthService.change_password")
    @patch("modules.auth.controllers.auth_controller.AuthService.get_user_by_id")
    @patch.object(AuthController, "_get_payload_from_request", return_value={"sub": "1"})
    def test_cambio_password_renueva_cookie_y_access_token(self, payload, get_user, change_password, generate_tokens):
        user = SimpleNamespace(id=1, nombre_usuario="user", mail="user@example.com", rol=SimpleNamespace(nombre="GESTOR"), primer_login=False)
        get_user.return_value = user
        change_password.return_value = user
        generate_tokens.return_value = {
            "access_token": "new-access", "refresh_token": "new-refresh",
            "access_expires_at": "2026-09-10T12:15:00Z",
            "session_expires_at": "2026-09-17T12:00:00Z",
            "session_warning_seconds": 300,
        }
        response = self.client.post("/api/v1/auth/cambiar-password", json={
            "password_actual": "password123", "password_nueva": "password456",
            "password_confirmacion": "password456",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["access_token"], "new-access")
        self.assertNotIn("refresh_token", response.get_json())
        self.assertIn("gidas_refresh=new-refresh", response.headers["Set-Cookie"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        generate_tokens.assert_called_once()

    @patch("modules.auth.controllers.auth_controller.AuthService.refresh_tokens")
    def test_refresh_solo_acepta_cookie_y_origen_permitido(self, refresh):
        refresh.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "access_expires_at": "2026-09-10T12:15:00Z",
            "session_expires_at": "2026-09-17T12:00:00Z",
            "session_warning_seconds": 300,
            "user": {"id": 1, "nombre_usuario": "user"},
        }
        self.client.set_cookie("gidas_refresh", "old-refresh", path="/api/v1/auth")

        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": "https://gidas.example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            "access_token": "new-access",
            "access_expires_at": "2026-09-10T12:15:00Z",
            "session_expires_at": "2026-09-17T12:00:00Z",
            "session_warning_seconds": 300,
            "user": {"id": 1, "nombre_usuario": "user"},
        })
        refresh.assert_called_once_with("old-refresh", metadata=unittest.mock.ANY)
        self.assertIn("gidas_refresh=new-refresh", response.headers["Set-Cookie"])

    @patch("modules.auth.controllers.auth_controller.AuthService.refresh_tokens")
    def test_refresh_rechaza_json_y_origen_ausente_antes_del_service(self, refresh):
        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "json-token"},
        )

        self.assertEqual(response.status_code, 403)
        refresh.assert_not_called()
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    @patch("modules.auth.controllers.auth_controller.AuthService.refresh_tokens")
    def test_refresh_acepta_referer_permitido_si_origin_no_esta(self, refresh):
        refresh.return_value = {
            "access_token": "a",
            "refresh_token": "r2",
            "access_expires_at": "2026-09-10T12:15:00Z",
            "session_expires_at": "2026-09-17T12:00:00Z",
            "session_warning_seconds": 300,
            "user": {"id": 1},
        }
        self.client.set_cookie("gidas_refresh", "r1", path="/api/v1/auth")

        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={"Referer": "https://gidas.example.com/app/page"},
        )

        self.assertEqual(response.status_code, 200)
        refresh.assert_called_once()

    @patch("modules.auth.controllers.auth_controller.AuthService.refresh_tokens")
    def test_refresh_rechaza_origin_null_aunque_referer_sea_permitido(self, refresh):
        self.client.set_cookie("gidas_refresh", "r1", path="/api/v1/auth")

        response = self.client.post(
            "/api/v1/auth/refresh",
            headers={
                "Origin": "null",
                "Referer": "https://gidas.example.com/app/page",
            },
        )

        self.assertEqual(response.status_code, 403)
        refresh.assert_not_called()

    @patch("modules.auth.controllers.auth_controller.AuthService.refresh_tokens")
    def test_refresh_rechaza_origin_con_sintaxis_no_valida(self, refresh):
        self.client.set_cookie("gidas_refresh", "r1", path="/api/v1/auth")

        invalid_origins = (
            "https://gidas.example.com/app",
            "https://gidas.example.com?next=/app",
            "https://user@gidas.example.com",
            "https://gidas.example.com#fragment",
        )
        for origin in invalid_origins:
            with self.subTest(origin=origin):
                response = self.client.post(
                    "/api/v1/auth/refresh",
                    headers={"Origin": origin},
                )
                self.assertEqual(response.status_code, 403)

        refresh.assert_not_called()

    @patch("modules.auth.controllers.auth_controller.AuthService.revoke_refresh_token")
    def test_logout_es_idempotente_y_siempre_borra_cookie(self, revoke):
        revoke.side_effect = Exception("invalid")
        self.client.set_cookie("gidas_refresh", "invalid", path="/api/v1/auth")

        response = self.client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "https://gidas.example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("gidas_refresh=;", response.headers["Set-Cookie"])
        self.assertIn("Expires=Thu, 01 Jan 1970", response.headers["Set-Cookie"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    @patch("modules.auth.controllers.auth_controller.AuthService.revoke_refresh_token")
    def test_logout_rechaza_origen_no_permitido_sin_revocar_ni_borrar_cookie(self, revoke):
        self.client.set_cookie("gidas_refresh", "token", path="/api/v1/auth")

        response = self.client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "https://evil.example"},
        )

        self.assertEqual(response.status_code, 403)
        revoke.assert_not_called()
        self.assertNotIn("Set-Cookie", response.headers)


if __name__ == "__main__":
    unittest.main()
