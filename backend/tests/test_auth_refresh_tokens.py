import concurrent.futures
import datetime
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from flask import Flask

from extension import db
from modules.auth.models.persona import Persona  # noqa: F401
from modules.auth.models.refresh_token_session import RefreshTokenSession
from modules.auth.models.usuario import RolUsuario, Usuario
from modules.auth.services.auth_service import AuthService


class AuthRefreshTokenTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)

        with self.app.app_context():
            db.create_all()
            rol = RolUsuario(nombre="GESTOR")
            db.session.add(rol)
            db.session.flush()

            self.user = Usuario(
                nombre_usuario="usuario.refresh",
                mail="refresh@example.com",
                id_rol=rol.id,
                primer_login=False,
            )
            self.user.set_password("password123")
            db.session.add(self.user)
            db.session.commit()
            self.user_id = self.user.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _login(self):
        return AuthService.login(
            "usuario.refresh",
            "password123",
            metadata={
                "user_agent": "pytest-agent",
                "ip_address": "127.0.0.1",
            },
        )

    def test_login_persiste_hash_y_metadata_de_refresh_token(self):
        with self.app.app_context():
            tokens = self._login()
            session = RefreshTokenSession.query.one()

            self.assertEqual(session.user_id, self.user_id)
            self.assertNotEqual(session.token_hash, tokens["refresh_token"])
            self.assertEqual(len(session.token_hash), 64)
            self.assertEqual(session.user_agent, "pytest-agent")
            self.assertEqual(session.ip_address, "127.0.0.1")
            self.assertIsNone(session.revoked_at)

    def test_refresh_rota_token_y_revoca_el_anterior(self):
        with self.app.app_context():
            tokens = self._login()
            rotated = AuthService.refresh_tokens(tokens["refresh_token"])

            self.assertIn("access_token", rotated)
            self.assertIn("refresh_token", rotated)
            self.assertEqual(rotated["user"], {
                "id": self.user_id,
                "nombre_usuario": "usuario.refresh",
                "mail": "refresh@example.com",
                "rol": "GESTOR",
                "primer_login": False,
            })
            self.assertNotEqual(tokens["refresh_token"], rotated["refresh_token"])

            sessions = RefreshTokenSession.query.order_by(RefreshTokenSession.id).all()
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sessions[0].revoked_reason, "rotated")
            self.assertEqual(sessions[0].replaced_by_id, sessions[1].id)
            self.assertIsNone(sessions[1].revoked_at)

            with self.assertRaisesRegex(Exception, "revocado"):
                AuthService.refresh_tokens(tokens["refresh_token"])

            db.session.refresh(sessions[1])
            self.assertIsNone(sessions[1].revoked_at)

    def test_refresh_rechaza_usuario_inactivo(self):
        with self.app.app_context():
            tokens = self._login()
            user = db.session.get(Usuario, self.user_id)
            user.activo = False
            db.session.commit()

            with self.assertRaisesRegex(Exception, "Usuario no encontrado"):
                AuthService.refresh_tokens(tokens["refresh_token"])

    def test_refresh_rechaza_sesion_vencida_aunque_el_jwt_siga_vigente(self):
        with self.app.app_context():
            tokens = self._login()
            session = RefreshTokenSession.query.one()
            session.expires_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
            db.session.commit()

            with self.assertRaisesRegex(Exception, "expirado"):
                AuthService.refresh_tokens(tokens["refresh_token"])

            db.session.refresh(session)
            self.assertEqual(session.revoked_reason, "expired")

    def test_cambio_password_revoca_sesiones_activas(self):
        with self.app.app_context():
            tokens = self._login()

            AuthService.change_password(
                self.user_id,
                "password123",
                "password456",
            )

            session = RefreshTokenSession.query.one()
            self.assertEqual(session.revoked_reason, "password_changed")

            with self.assertRaisesRegex(Exception, "revocado"):
                AuthService.refresh_tokens(tokens["refresh_token"])

    def test_cambio_password_permite_renovar_sesion_nueva(self):
        with self.app.app_context():
            previous = self._login()
            user = AuthService.change_password(self.user_id, "password123", "password456")
            new_tokens = AuthService.generate_tokens(user, persist_refresh=True)

            with self.assertRaisesRegex(Exception, "revocado"):
                AuthService.refresh_tokens(previous["refresh_token"])
            renewed = AuthService.refresh_tokens(new_tokens["refresh_token"])
            self.assertEqual(renewed["user"]["id"], self.user_id)

    def test_logout_revoca_refresh_token_actual(self):
        with self.app.app_context():
            tokens = self._login()

            AuthService.revoke_refresh_token(tokens["refresh_token"])

            session = RefreshTokenSession.query.one()
            self.assertEqual(session.revoked_reason, "logout")

            with self.assertRaisesRegex(Exception, "revocado"):
                AuthService.refresh_tokens(tokens["refresh_token"])

    def test_error_durante_rotacion_revierte_reclamacion(self):
        with self.app.app_context():
            tokens = self._login()

            with patch.object(
                AuthService,
                "_generate_access_token",
                side_effect=RuntimeError("fallo controlado"),
            ):
                with self.assertRaisesRegex(RuntimeError, "fallo controlado"):
                    AuthService.refresh_tokens(tokens["refresh_token"])

            session = RefreshTokenSession.query.one()
            self.assertIsNone(session.revoked_at)
            self.assertIsNone(session.revoked_reason)


class AuthConcurrentRefreshTokenTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "refresh-concurrency.db")
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)

        with self.app.app_context():
            db.create_all()
            role = RolUsuario(nombre="GESTOR")
            db.session.add(role)
            db.session.flush()
            user = Usuario(
                nombre_usuario="usuario.concurrente",
                mail="concurrente@example.com",
                id_rol=role.id,
                primer_login=False,
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            self.refresh_token = AuthService.login(
                "usuario.concurrente",
                "password123",
            )["refresh_token"]

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.temp_dir.cleanup()

    def test_doble_refresh_concurrente_solo_rota_una_vez(self):
        barrier = threading.Barrier(2)
        original_claim = AuthService._claim_refresh_session

        def synchronized_claim(session_id, claimed_at):
            barrier.wait(timeout=5)
            return original_claim(session_id, claimed_at)

        def refresh_once():
            with self.app.app_context():
                try:
                    return AuthService.refresh_tokens(self.refresh_token)
                except Exception as exc:
                    return exc
                finally:
                    db.session.remove()

        with patch.object(
            AuthService,
            "_claim_refresh_session",
            side_effect=synchronized_claim,
        ):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: refresh_once(), range(2)))

        successes = [result for result in results if isinstance(result, dict)]
        failures = [result for result in results if isinstance(result, Exception)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertRegex(str(failures[0]), "revocado")

        with self.app.app_context():
            sessions = RefreshTokenSession.query.order_by(RefreshTokenSession.id).all()
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sessions[0].revoked_reason, "rotated")
            self.assertEqual(sessions[0].replaced_by_id, sessions[1].id)


if __name__ == "__main__":
    unittest.main()
