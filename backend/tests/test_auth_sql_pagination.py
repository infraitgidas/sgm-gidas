import unittest
from unittest.mock import patch

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.auth.models.usuario import RolUsuario, Usuario
from modules.auth.services.auth_service import AuthService
from modules.auth.controllers.auth_controller import AuthController


class AuthSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        role = RolUsuario(nombre="ADMIN")
        db.session.add(role)
        db.session.flush()
        db.session.add_all(
            Usuario(nombre_usuario=f"usuario{index:02}", mail=f"u{index:02}@example.com",
                    contrasena="hash", id_rol=role.id, activo=True)
            for index in range(12)
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_sql_y_contrato_administrador(self):
        statements = []

        def record(_conn, _cursor, sql, _params, _context, _many):
            if "from usuario" in sql.lower():
                statements.append(sql.lower())

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            users, total = AuthService.get_users_page(2, 3)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertEqual(total, 12)
        self.assertEqual([user.nombre_usuario for user in users], [f"usuario{i:02}" for i in (3, 4, 5)])
        self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))

        with patch.object(AuthController, "_get_payload_from_request", return_value={"rol": "ADMIN", "sub": "1"}):
            with self.app.test_request_context("/auth/usuarios?page=2&per_page=3"):
                response, status = AuthController.get_all_users()
                self.assertEqual(status, 200)
                self.assertEqual(response.get_json()["meta"]["total"], 12)
                self.assertEqual(len(response.get_json()["data"]), 3)
            with self.app.test_request_context("/auth/usuarios?page=0"):
                response, status = AuthController.get_all_users()
                self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
