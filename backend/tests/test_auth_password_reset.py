import datetime as dt
import re
import os
import importlib.util
import uuid
import unittest
from pathlib import Path
from threading import Barrier, Thread
from unittest.mock import patch

from cryptography.fernet import Fernet
from flask import Flask
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from alembic.migration import MigrationContext
from alembic.operations import Operations

from extension import db
from modules import models_registry  # noqa: F401
from modules.auth.controllers.password_reset_controller import PasswordResetController, email_rate_key
from modules.auth.models.persona import Persona  # noqa: F401
from modules.auth.models.password_reset_request import PasswordResetRequest
from modules.auth.models.refresh_token_session import RefreshTokenSession
from modules.auth.models.usuario import Usuario, RolUsuario
from modules.auth.services.auth_service import AuthService
from modules.auth.services.credentials_policy import normalize_email, validate_password
from modules.auth.services.password_reset_service import InvalidPasswordResetToken, PasswordResetService
from modules.notifications.models.email_outbox import EmailOutbox
from modules.notifications.services.email_worker import EmailWorker, RETRY_MINUTES, purge_notifications
from modules.notifications.services.payload_cipher import decrypt_payload
from modules.notifications.services.settings import validate_email_settings
from modules.shared.exceptions import ValidationError


class RecordingTransport:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send(self, message_id, payload):
        if self.fail: raise OSError("Sensitive SMTP detail MUST NOT be logged")
        self.sent.append((message_id, payload))


class PasswordResetTests(unittest.TestCase):
    database_uri = "sqlite:///:memory:"
    engine_options = {}

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=self.database_uri,
            SQLALCHEMY_ENGINE_OPTIONS=self.engine_options,
            SQLALCHEMY_TRACK_MODIFICATIONS=False, SECRET_KEY="app-secret" * 5,
            EMAIL_OUTBOX_ENCRYPTION_KEY=Fernet.generate_key().decode(), PASSWORD_RESET_HMAC_KEY="h" * 40,
            PASSWORD_RESET_PUBLIC_URL="http://localhost/restablecer-password")
        db.init_app(self.app)
        self.app.add_url_rule("/request", view_func=PasswordResetController.request_public, methods=["POST"])
        self.app.add_url_rule("/confirm", view_func=PasswordResetController.confirm, methods=["POST"])
        self.context = self.app.app_context(); self.context.push()
        if db.engine.dialect.name == "sqlite":
            with db.engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        db.create_all()
        role = RolUsuario(nombre="GESTOR"); db.session.add(role); db.session.flush()
        user = Usuario(nombre_usuario="test.reset", mail="reset@example.com", id_rol=role.id, primer_login=True)
        user.set_password("old-password"); db.session.add(user); db.session.commit(); self.user_id = user.id

    def tearDown(self):
        db.session.remove()
        with db.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        db.drop_all(); self.context.pop()

    def request(self):
        PasswordResetService.request_public(" RESET@EXAMPLE.COM ", "127.0.0.1")
        reset = PasswordResetRequest.query.filter_by(revoked_at=None, consumed_at=None).one()
        message = db.session.get(EmailOutbox, reset.email_message_id)
        payload = decrypt_payload(message.payload_encrypted)
        token = re.search(r"#token=([A-Za-z0-9_-]{43})", payload["text"]).group(1)
        return reset, message, token

    def send(self, message):
        transport = RecordingTransport(); worker = EmailWorker(transport)
        claim = worker.claim()[0]; self.assertEqual(claim[0], message.id)
        self.assertTrue(worker.process(*claim))
        return transport

    def test_public_same_response_unknown_disabled_deleted_and_failure(self):
        client = self.app.test_client()
        known = client.post("/request", json={"email": "reset@example.com"})
        unknown = client.post("/request", json={"email": "missing@example.com"})
        self.assertEqual(known.status_code, 202); self.assertEqual(known.json, unknown.json)
        self.assertEqual(known.headers["Cache-Control"], "no-store")
        self.assertEqual(PasswordResetRequest.query.count(), 1)
        user = db.session.get(Usuario, self.user_id); user.activo = False; db.session.commit()
        self.assertEqual(client.post("/request", json={"email": "reset@example.com"}).json, known.json)
        user.activo = True; user.deleted_at = dt.datetime.utcnow(); db.session.commit()
        self.assertEqual(client.post("/request", json={"email": "reset@example.com"}).json, known.json)
        user.deleted_at = None; db.session.commit()
        with patch("modules.auth.services.password_reset_service.encrypt_payload", side_effect=RuntimeError("internal secret")):
            self.assertEqual(client.post("/request", json={"email": "reset@example.com"}).json, known.json)

    def test_policy_and_email_normalization(self):
        self.assertEqual(normalize_email(" USER@Example.COM "), "user@example.com")
        for value in (None, "bad", "x\n@example.com", "x" * 121 + "@test.com"):
            with self.assertRaises(ValidationError): normalize_email(value)
        for value in (None, {}, "short", "😀" * 19):
            with self.assertRaises(ValidationError): validate_password(value)
        self.assertEqual(validate_password("123456"), "123456")
        self.assertEqual(self.app.test_client().post("/request", json={"email": "bad"}).status_code, 400)

    def test_cipher_hash_fragment_and_inactive_until_smtp(self):
        reset, message, token = self.request()
        self.assertNotIn(token, message.payload_encrypted); self.assertNotIn("reset@example.com", message.payload_encrypted)
        self.assertNotEqual(reset.token_hash, token); self.assertEqual(len(reset.token_hash), 64)
        self.assertNotEqual(reset.requested_ip_hmac, "127.0.0.1")
        self.assertIsNone(reset.expires_at)
        with self.assertRaises(InvalidPasswordResetToken): PasswordResetService.confirm(token, "new-password", "new-password")

    def test_smtp_activation_confirm_single_use_and_refresh_revocation(self):
        tokens = AuthService.login("test.reset", "old-password")
        reset, message, token = self.request(); self.send(message)
        self.assertIsNone(message.payload_encrypted); self.assertEqual(message.status, "sent")
        self.assertEqual(reset.expires_at - reset.activated_at, dt.timedelta(minutes=30))
        response = self.app.test_client().post("/confirm", json={"token": token, "password_nueva": "new-password", "password_confirmacion": "new-password"})
        self.assertEqual(response.status_code, 200); self.assertNotIn("access_token", response.json["data"])
        user = db.session.get(Usuario, self.user_id); self.assertTrue(user.verificar_password("new-password")); self.assertFalse(user.primer_login)
        self.assertEqual(RefreshTokenSession.query.one().revoked_reason, "password_reset")
        with self.assertRaises(Exception): AuthService.refresh_tokens(tokens["refresh_token"])
        with self.assertRaises(InvalidPasswordResetToken): PasswordResetService.confirm(token, "another-password", "another-password")

    def test_replacement_cancels_claimed_message_and_clears_payload(self):
        reset, message, token = self.request(); transport = RecordingTransport(); worker = EmailWorker(transport)
        claim = worker.claim()[0]; self.request()
        db.session.refresh(reset); db.session.refresh(message)
        self.assertIsNotNone(reset.revoked_at); self.assertEqual(message.status, "cancelled"); self.assertIsNone(message.payload_encrypted)
        self.assertFalse(worker.process(*claim)); self.assertEqual(transport.sent, [])
        self.assertEqual(PasswordResetRequest.query.filter_by(consumed_at=None, revoked_at=None).count(), 1)

    def test_all_invalid_token_states_have_same_public_error(self):
        reset, message, token = self.request()
        client = self.app.test_client()
        body = {"token": token, "password_nueva": "new-password", "password_confirmacion": "new-password"}
        initial = client.post("/confirm", json=body)
        self.assertEqual(initial.status_code, 400)
        self.assertEqual(initial.json["error"]["code"], "INVALID_PASSWORD_RESET_TOKEN")
        self.send(message)
        reset.expires_at = dt.datetime.utcnow() - dt.timedelta(seconds=1)
        reset.activated_at = reset.expires_at - dt.timedelta(minutes=30); db.session.commit()
        self.assertEqual(client.post("/confirm", json=body).json, initial.json)
        body["token"] = "x" * 43
        self.assertEqual(client.post("/confirm", json=body).json, initial.json)
        body["token"] = ["wrong"]
        self.assertEqual(client.post("/confirm", json=body).json, initial.json)

    def test_password_fields_and_unavailable_user(self):
        reset, message, token = self.request(); self.send(message)
        with self.assertRaises(ValidationError): PasswordResetService.confirm(token, "short", "short")
        with self.assertRaises(ValidationError): PasswordResetService.confirm(token, "long-password", "different")
        user = db.session.get(Usuario, self.user_id); user.activo = False; db.session.commit()
        with self.assertRaises(InvalidPasswordResetToken): PasswordResetService.confirm(token, "new-password", "new-password")

    def test_retries_are_five_after_initial_then_terminal_without_sensitive_log(self):
        reset, message, token = self.request(); worker = EmailWorker(RecordingTransport(fail=True))
        now = dt.datetime.utcnow()
        with self.assertLogs("modules.notifications.services.email_worker", level="WARNING") as captured:
            for attempt in range(1, 7):
                claim = worker.claim(now=now)[0]; self.assertFalse(worker.process(*claim, now=now))
                db.session.refresh(message)
                self.assertEqual(message.attempt_count, attempt)
                if attempt < 6:
                    self.assertEqual(message.next_attempt_at - now, dt.timedelta(minutes=RETRY_MINUTES[attempt - 1])); now = message.next_attempt_at
        self.assertEqual(message.status, "failed"); self.assertIsNone(message.payload_encrypted)
        db.session.refresh(reset); self.assertIsNotNone(reset.revoked_at)
        self.assertNotIn("Sensitive SMTP", " ".join(captured.output)); self.assertNotIn(token, " ".join(captured.output))

    def test_leases_recover_and_old_worker_cannot_finalize(self):
        reset, message, token = self.request(); worker = EmailWorker(RecordingTransport()); now = dt.datetime.utcnow()
        old_claim = worker.claim(now=now)[0]
        self.assertEqual(worker.claim(now=now), [])
        new_claim = worker.claim(now=now + dt.timedelta(minutes=6))[0]
        self.assertNotEqual(old_claim[1], new_claim[1]); self.assertFalse(worker.process(*old_claim))
        self.assertTrue(worker.process(*new_claim))

    def test_claim_caps_batch_and_retention_respects_windows(self):
        reset, message, token = self.request(); self.send(message)
        now = dt.datetime.utcnow(); message.sent_at = now - dt.timedelta(days=8); db.session.commit()
        self.assertEqual(purge_notifications(now)["messages_deleted"], 1)
        db.session.expire_all(); self.assertIsNone(db.session.get(PasswordResetRequest, reset.id).email_message_id)
        reset = db.session.get(PasswordResetRequest, reset.id); reset.consumed_at = now - dt.timedelta(days=31); db.session.commit()
        self.assertEqual(purge_notifications(now)["requests_deleted"], 1)

    def test_email_rate_key_is_hmac_and_normalized(self):
        with self.app.test_request_context(json={"email": " Reset@EXAMPLE.com "}): first = email_rate_key()
        with self.app.test_request_context(json={"email": "reset@example.com"}): self.assertEqual(first, email_rate_key())
        self.assertEqual(len(first), 64); self.assertNotIn("example", first)

    def test_config_tls_url_and_independent_secrets(self):
        cfg = dict(self.app.config, APP_ENV="production", FRONTEND_URLS=["https://gidas.example"],
                   PASSWORD_RESET_PUBLIC_URL="https://gidas.example/restablecer-password", MAIL_SERVER="smtp.example",
                   MAIL_DEFAULT_SENDER="GIDAS <no-reply@example.com>", SMTP_TLS_MODE="starttls", SMTP_TIMEOUT_SECONDS=20)
        validate_email_settings(cfg)
        for change in ({"SMTP_TLS_MODE": "none"}, {"PASSWORD_RESET_PUBLIC_URL": "http://gidas.example/restablecer-password"},
                       {"PASSWORD_RESET_HMAC_KEY": cfg["SECRET_KEY"]}, {"EMAIL_OUTBOX_ENCRYPTION_KEY": "not-a-key"},
                       {"PASSWORD_RESET_PUBLIC_URL": "https://other.example/restablecer-password"}):
            with self.assertRaises(RuntimeError): validate_email_settings(dict(cfg, **change))

    def test_email_edit_cancels_previous_link_and_admin_attribution(self):
        reset, message, _token = self.request()
        AuthService.update_user(self.user_id, {"mail": " UPDATED@EXAMPLE.COM "}, self.user_id)
        db.session.refresh(reset); db.session.refresh(message)
        self.assertIsNotNone(reset.revoked_at)
        self.assertEqual(message.status, "cancelled")
        self.assertEqual(db.session.get(Usuario, self.user_id).mail, "updated@example.com")
        PasswordResetService.request_admin(self.user_id, self.user_id, "127.0.0.1")
        latest = PasswordResetRequest.query.filter_by(revoked_at=None, consumed_at=None).one()
        self.assertEqual(latest.requested_by_admin_id, self.user_id)

    def test_versioned_routes_allow_public_flow_and_enforce_admin_role(self):
        from extension import limiter
        from modules.auth.models.usuario_grupo_utn import UsuarioGrupoUtn
        from modules.auth.routes.auth_rutas import auth_bp
        from modules.grupo.models.grupo import GrupoInvestigacionUtn
        from modules.shared.services.tenant_request import register_tenant_request_scope
        from modules.shared.services.tenant_scope import register_tenant_orm_policy
        group = GrupoInvestigacionUtn(nombre_sigla_grupo="UCT recuperacion", nombre_unidad_academica="UTN",
            mail="uct@example.com", objetivo_desarrollo="Investigacion", created_by=self.user_id)
        db.session.add(group); db.session.flush()
        db.session.add(UsuarioGrupoUtn(usuario_id=self.user_id, grupo_utn_id=group.id, created_by=self.user_id))
        db.session.commit()
        self.app.config["RATELIMIT_ENABLED"] = False
        limiter.init_app(self.app)
        self.app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
        register_tenant_request_scope(self.app)
        register_tenant_orm_policy()
        client = self.app.test_client()
        self.assertEqual(client.post("/api/v1/auth/password-reset/request", json={"email": "reset@example.com"}).status_code, 202)
        self.assertEqual(client.post("/api/v1/auth/password-reset/confirm", json={"token": "bad", "password_nueva": "123456", "password_confirmacion": "123456"}).status_code, 400)
        admin_path = f"/api/v1/auth/usuarios/{self.user_id}/password-reset"
        self.assertEqual(client.post(admin_path).status_code, 401)
        with patch.object(AuthService, "verify_token", return_value={"sub": str(self.user_id), "rol": "GESTOR"}):
            self.assertEqual(client.post(admin_path, headers={"Authorization": "Bearer mocked"}).status_code, 403)
        role = RolUsuario(nombre="ADMIN"); db.session.add(role); db.session.flush()
        db.session.get(Usuario, self.user_id).id_rol = role.id; db.session.commit()
        outsider = Usuario(nombre_usuario="other.reset", mail="other@example.com", id_rol=role.id)
        outsider.set_password("other-password"); db.session.add(outsider); db.session.commit()
        outsider_id = outsider.id
        with patch.object(AuthService, "verify_token", return_value={"sub": str(self.user_id), "rol": "ADMIN"}):
            response = client.post(admin_path, headers={"Authorization": "Bearer mocked"})
            self.assertEqual(response.status_code, 202)
            self.assertNotIn("token", response.get_data(as_text=True))
            response = client.post(f"/api/v1/auth/usuarios/{outsider_id}/password-reset", headers={"Authorization": "Bearer mocked"})
            self.assertEqual(response.status_code, 404)

    def test_request_limits_email_across_ips_and_ip_across_emails(self):
        from extension import limiter
        from modules.auth.routes.auth_rutas import auth_bp
        from modules.shared.services.error_handlers import register_error_handlers
        self.app.config.update(RATELIMIT_ENABLED=True, RATELIMIT_STORAGE_URI="memory://",
            PASSWORD_RESET_REQUEST_IP_LIMIT="5 per 15 minutes", PASSWORD_RESET_REQUEST_EMAIL_LIMIT="3 per hour")
        limiter.init_app(self.app)
        self.app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
        register_error_handlers(self.app)
        client = self.app.test_client(); path = "/api/v1/auth/password-reset/request"
        for index in range(3):
            self.assertEqual(client.post(path, json={"email": " RESET@EXAMPLE.COM "}, environ_overrides={"REMOTE_ADDR": f"10.0.0.{index}"}).status_code, 202)
        response = client.post(path, json={"email": "reset@example.com"}, environ_overrides={"REMOTE_ADDR": "10.0.1.1"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json["error"]["code"], "RATE_LIMIT_EXCEEDED")
        for index in range(5):
            self.assertEqual(client.post(path, json={"email": f"unknown{index}@example.com"}, environ_overrides={"REMOTE_ADDR": "10.1.0.1"}).status_code, 202)
        self.assertEqual(client.post(path, json={"email": "another@example.com"}, environ_overrides={"REMOTE_ADDR": "10.1.0.1"}).status_code, 429)

    def test_smtp_requires_starttls_before_login_and_rejects_refused_delivery(self):
        import smtplib
        from modules.notifications.services.smtp_transport import SMTPTransport
        self.app.config.update(MAIL_SERVER="smtp.example", MAIL_PORT=587, SMTP_TLS_MODE="starttls",
            SMTP_TIMEOUT_SECONDS=20, MAIL_DEFAULT_SENDER="no-reply@example.com", MAIL_USERNAME="smtp-user", MAIL_PASSWORD="smtp-password")
        payload = {"to": "recipient@example.com", "subject": "Reset", "text": "Body", "html": "<p>Body</p>"}
        with patch("modules.notifications.services.smtp_transport.smtplib.SMTP") as factory:
            smtp = factory.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            SMTPTransport().send("message-id", payload)
            names = [call[0] for call in smtp.method_calls]
            self.assertLess(names.index("starttls"), names.index("login"))
            self.assertLess(names.index("login"), names.index("send_message"))
            factory.assert_called_once_with("smtp.example", 587, timeout=20)
            self.assertTrue(smtp.starttls.call_args.kwargs["context"].check_hostname)
            smtp.send_message.return_value = {"recipient@example.com": (550, b"private detail")}
            with self.assertRaises(smtplib.SMTPRecipientsRefused): SMTPTransport().send("message-id", payload)


@unittest.skipUnless(os.getenv("PASSWORD_RESET_PG_TEST") == "1", "PostgreSQL dedicado requerido")
class PasswordResetPostgresTests(PasswordResetTests):
    def setUp(self):
        from config import Config
        url = make_url(Config.SQLALCHEMY_DATABASE_URI).set(database="gidas_reset_validation")
        self.admin_engine = create_engine(url)
        self.schema = "reset_" + uuid.uuid4().hex
        with self.admin_engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public"))
            connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.database_uri = url
        self.engine_options = {"connect_args": {"options": f"-csearch_path={self.schema},public"}}
        super().setUp()

    def tearDown(self):
        db.session.remove(); db.engine.dispose(); self.context.pop()
        with self.admin_engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        self.admin_engine.dispose()

    def concurrently(self, operation):
        barrier = Barrier(2); outcomes = []; errors = []
        def run():
            with self.app.app_context():
                try:
                    barrier.wait(timeout=10)
                    outcomes.append(operation())
                except Exception as error:
                    errors.append(error)
                    db.session.rollback()
                finally: db.session.remove()
        threads = [Thread(target=run) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads:
            thread.join(timeout=20)
            self.assertFalse(thread.is_alive(), "Operacion concurrente bloqueada")
        return outcomes, errors

    def test_concurrent_confirmation_consumes_exactly_once(self):
        _reset, message, token = self.request(); self.send(message)
        db.session.remove()
        outcomes, errors = self.concurrently(lambda: PasswordResetService.confirm(token, "new-password", "new-password"))
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], InvalidPasswordResetToken)
        self.assertEqual(PasswordResetRequest.query.filter(PasswordResetRequest.consumed_at.isnot(None)).count(), 1)

    def test_concurrent_claims_are_disjoint_and_cap_twenty(self):
        for _ in range(45):
            db.session.add(EmailOutbox(message_type="password_reset", status="pending", payload_encrypted="opaque"))
        db.session.commit(); db.session.remove()
        outcomes, errors = self.concurrently(lambda: EmailWorker().claim(limit=100))
        self.assertEqual(errors, [])
        self.assertEqual([len(batch) for batch in outcomes], [20, 20])
        ids = [message_id for batch in outcomes for message_id, _lease in batch]
        self.assertEqual(len(set(ids)), 40)

    def test_migration_duplicate_guard_upgrade_downgrade_upgrade(self):
        spec = importlib.util.spec_from_file_location("reset_migration", Path(__file__).parents[1] / "migrations/versions/e5a7c9d1f3b6_password_reset_outbox.py")
        migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
        schema = self.schema + "_migration"
        with self.admin_engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
            connection.execute(text(f"SET LOCAL search_path TO {schema}"))
            connection.execute(text("CREATE TABLE usuario (id integer PRIMARY KEY, mail varchar(120) NOT NULL UNIQUE)"))
            connection.execute(text("INSERT INTO usuario VALUES (1, ' USER@example.com '), (2, 'user@example.com')"))
            with Operations.context(MigrationContext.configure(connection)):
                with self.assertRaisesRegex(RuntimeError, "duplicados"): migration.upgrade()
            connection.execute(text("DELETE FROM usuario WHERE id=2"))
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade(); migration.downgrade(); migration.upgrade()
            self.assertEqual(connection.execute(text("SELECT mail FROM usuario")).scalar(), "user@example.com")
            self.assertIsNotNone(connection.execute(text("SELECT to_regclass('password_reset_request')")).scalar())
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))


if __name__ == "__main__": unittest.main()
