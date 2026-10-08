import concurrent.futures
import datetime
import os
import tempfile
import unittest

from flask import Flask

from config import Config
from extension import db
from modules.auth.controllers.auth_controller import AuthController
from modules.auth.models.persona import Persona  # noqa: F401
from modules.auth.models.login_attempt import LoginAttempt
from modules.auth.models.refresh_token_session import RefreshTokenSession
from modules.auth.models.usuario import RolUsuario, Usuario
from modules.auth.services.auth_service import AuthService


class AuthLoginLockoutTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "login-lockout.db")
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="stable-test-secret",
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path.replace(os.sep, '/')}",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"timeout": 15}},
        )
        for key in (
            "REFRESH_COOKIE_NAME", "REFRESH_COOKIE_HTTPONLY", "REFRESH_COOKIE_SECURE",
            "REFRESH_COOKIE_SAMESITE", "REFRESH_COOKIE_PATH",
            "REFRESH_TOKEN_EXPIRATION_MINUTES",
        ):
            self.app.config[key] = getattr(Config, key)
        db.init_app(self.app)
        self.app.add_url_rule("/login", view_func=AuthController.login, methods=["POST"])
        with self.app.app_context():
            db.create_all()
            role = RolUsuario(nombre="GESTOR")
            db.session.add(role)
            db.session.flush()
            for name in ("usuario.uno", "usuario.dos"):
                user = Usuario(
                    nombre_usuario=name,
                    mail=f"{name}@example.com",
                    id_rol=role.id,
                    primer_login=False,
                )
                user.set_password("clave-correcta")
                db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp_dir.cleanup()

    def _post(self, username, password="clave-incorrecta"):
        with self.app.test_client() as client:
            return client.post("/login", json={"nombre_usuario": username, "password": password})

    def _attempt(self, username):
        key = AuthService._login_identifier_hash(username)
        return LoginAttempt.query.filter_by(identifier_hash=key).one()

    def test_tercer_fallo_bloquea_y_no_emite_sesion_con_clave_correcta(self):
        for _ in range(2):
            response = self._post("usuario.uno")
            self.assertEqual(response.status_code, 401)
        response = self._post("usuario.uno")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "900")
        self.assertIn("15 minutos", response.json["error"]["message"])
        self.assertNotIn("Set-Cookie", response.headers)

        correct = self._post("usuario.uno", "clave-correcta")
        self.assertEqual(correct.status_code, 429)
        self.assertNotIn("Set-Cookie", correct.headers)
        self.assertEqual(self._post("usuario.dos", "clave-correcta").status_code, 200)
        with self.app.app_context():
            self.assertEqual(RefreshTokenSession.query.count(), 1)

    def test_usuario_inexistente_recibe_mismo_contrato_y_no_revela_existencia(self):
        contracts = []
        for username in ("usuario.uno", "usuario.inexistente"):
            responses = [self._post(username) for _ in range(3)]
            self.assertEqual([r.status_code for r in responses], [401, 401, 429])
            self.assertEqual(responses[-1].headers["Retry-After"], "900")
            contracts.append([(r.status_code, r.json["error"]["code"], r.json["error"]["message"]) for r in responses])
        self.assertEqual(contracts[0], contracts[1])

    def test_expiracion_reinicia_contador_y_exito_limpia_fallos(self):
        self._post("usuario.uno")
        self._post("usuario.uno")
        self._post("usuario.uno")
        with self.app.app_context():
            attempt = self._attempt("usuario.uno")
            attempt.locked_until = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
            db.session.commit()
        self.assertEqual(self._post("usuario.uno").status_code, 401)
        with self.app.app_context():
            attempt = self._attempt("usuario.uno")
            self.assertEqual(attempt.failed_count, 1)
            self.assertIsNone(attempt.locked_until)
        self.assertEqual(self._post("usuario.uno", "clave-correcta").status_code, 200)
        with self.app.app_context():
            self.assertEqual(self._attempt("usuario.uno").failed_count, 0)
        self.assertEqual(self._post("usuario.uno").status_code, 401)

    def test_cambio_de_clave_no_levanta_un_bloqueo_activo(self):
        for _ in range(3):
            self._post("usuario.uno")
        with self.app.app_context():
            user = Usuario.query.filter_by(nombre_usuario="usuario.uno").one()
            AuthService.change_password(user.id, "clave-correcta", "clave-nueva")
        self.assertEqual(self._post("usuario.uno", "clave-nueva").status_code, 429)

    def test_bloqueo_persiste_tras_cerrar_la_sesion_de_base_de_datos(self):
        for _ in range(3):
            self._post("usuario.uno")
        with self.app.app_context():
            db.session.remove()
        response = self._post("usuario.uno", "clave-correcta")
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers["Retry-After"]), 0)

    def test_tres_fallos_concurrentes_no_pierden_incrementos(self):
        def attempt(_):
            return self._post("usuario.uno").status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            statuses = list(pool.map(attempt, range(3)))
        self.assertEqual(sorted(statuses), [401, 401, 429])
        with self.app.app_context():
            state = self._attempt("usuario.uno")
            self.assertEqual(state.failed_count, 3)
            self.assertIsNotNone(state.locked_until)


if __name__ == "__main__":
    unittest.main()
