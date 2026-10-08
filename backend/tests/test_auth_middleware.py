import unittest
from unittest.mock import patch

from flask import Flask, g, request

from modules.auth.controllers.auth_controller import AuthController
from modules.shared.services.middleware import requiere_auth, requiere_rol


class AuthMiddlewareTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)

    def test_requiere_auth_carga_usuario_en_contexto(self):
        @requiere_auth
        def endpoint():
            return {"user_id": g.current_user_id, "rol": g.current_user_rol}

        with self.app.test_request_context(
            "/privado",
            headers={"Authorization": "Bearer token-valido"},
        ):
            with patch(
                "modules.shared.services.middleware.AuthService.verify_token",
                return_value={"sub": "12", "rol": "GESTOR"},
            ):
                response = endpoint()

        self.assertEqual(response, {"user_id": 12, "rol": "GESTOR"})

    def test_requiere_rol_rechaza_rol_no_permitido(self):
        @requiere_rol("ADMIN")
        def endpoint():
            return {"ok": True}

        with self.app.test_request_context(
            "/admin",
            headers={"Authorization": "Bearer token-valido"},
        ):
            with patch(
                "modules.shared.services.middleware.AuthService.verify_token",
                return_value={"sub": "12", "rol": "LECTURA"},
            ):
                response, status_code = endpoint()

        self.assertEqual(status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "FORBIDDEN")
        self.assertIn("no tiene permisos", response.get_json()["error"]["message"])

    def test_middleware_no_refleja_origin_manual(self):
        @self.app.route("/privado")
        @requiere_auth
        def privado():
            return {"ok": True}

        response = self.app.test_client().get(
            "/privado",
            headers={"Origin": "https://origen-no-permitido.example"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"]["code"], "AUTH_REQUIRED")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_controller_reutiliza_payload_del_contexto(self):
        with self.app.test_request_context("/perfil"):
            g.current_user_payload = {"sub": "9", "rol": "ADMIN"}
            g.tenant_request_marker = id(request._get_current_object())
            with patch(
                "modules.auth.controllers.auth_controller.AuthService.verify_token"
            ) as mock_verify_token:
                payload = AuthController._get_payload_from_request()

        self.assertEqual(payload, {"sub": "9", "rol": "ADMIN"})
        mock_verify_token.assert_not_called()

    def test_controller_no_expone_excepcion_inesperada(self):
        with self.app.test_request_context("/primer-usuario"):
            with patch(
                "modules.auth.controllers.auth_controller.AuthService.existe_primer_usuario",
                side_effect=RuntimeError("postgresql://usuario:secreto@db/interna"),
            ):
                response, status_code = AuthController.primer_usuario()

        body = response.get_json()
        self.assertEqual(status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("postgresql", str(body).lower())
        self.assertNotIn("secreto", str(body).lower())


if __name__ == "__main__":
    unittest.main()
