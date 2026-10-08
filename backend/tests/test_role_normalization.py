import unittest
from types import SimpleNamespace
from unittest.mock import patch

import sqlalchemy as sa

from migrations.versions.d7e4a2c9f1b6_normalize_lector_role_to_lectura import (
    _normalize_lector_role,
    _restore_lector_role,
)
from tools.seed_testing_data import _seed_roles


class RoleNormalizationMigrationTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = sa.create_engine("sqlite://")
        metadata = sa.MetaData()
        self.roles = sa.Table(
            "rol",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("nombre", sa.String(50), nullable=False, unique=True),
        )
        self.users = sa.Table(
            "usuario",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("id_rol", sa.Integer, nullable=False),
        )
        metadata.create_all(self.engine)

    def test_renombra_lector_conservando_id_y_usuarios(self):
        with self.engine.begin() as connection:
            connection.execute(
                self.roles.insert(),
                [{"id": 1, "nombre": "ADMIN"}, {"id": 3, "nombre": "LECTOR"}],
            )
            connection.execute(self.users.insert(), {"id": 10, "id_rol": 3})

            _normalize_lector_role(connection)

            role = connection.execute(
                sa.text("SELECT id, nombre FROM rol WHERE id = 3")
            ).one()
            user_role = connection.execute(
                sa.text("SELECT id_rol FROM usuario WHERE id = 10")
            ).scalar_one()

        self.assertEqual(role, (3, "LECTURA"))
        self.assertEqual(user_role, 3)

    def test_unifica_roles_duplicados_sin_dejar_usuarios_huerfanos(self):
        with self.engine.begin() as connection:
            connection.execute(
                self.roles.insert(),
                [
                    {"id": 3, "nombre": "LECTOR"},
                    {"id": 8, "nombre": "LECTURA"},
                ],
            )
            connection.execute(
                self.users.insert(),
                [{"id": 10, "id_rol": 3}, {"id": 11, "id_rol": 8}],
            )

            _normalize_lector_role(connection)

            roles = connection.execute(
                sa.text("SELECT id, nombre FROM rol ORDER BY id")
            ).all()
            user_roles = connection.execute(
                sa.text("SELECT id_rol FROM usuario ORDER BY id")
            ).scalars().all()

        self.assertEqual(roles, [(3, "LECTURA")])
        self.assertEqual(user_roles, [3, 3])

    def test_downgrade_restaura_el_nombre_anterior(self):
        with self.engine.begin() as connection:
            connection.execute(
                self.roles.insert(), {"id": 3, "nombre": "LECTURA"}
            )

            _restore_lector_role(connection)

            role_name = connection.execute(
                sa.text("SELECT nombre FROM rol WHERE id = 3")
            ).scalar_one()

        self.assertEqual(role_name, "LECTOR")


class TestingSeedRoleContractTestCase(unittest.TestCase):

    @patch("tools.seed_testing_data._get_or_create")
    def test_seed_testing_crea_solo_roles_canonicos(self, get_or_create):
        get_or_create.side_effect = lambda _model, nombre: (
            SimpleNamespace(nombre=nombre),
            True,
        )

        roles = _seed_roles()

        self.assertEqual(set(roles), {"ADMIN", "GESTOR", "LECTURA"})
        self.assertNotIn("LECTOR", roles)


if __name__ == "__main__":
    unittest.main()
