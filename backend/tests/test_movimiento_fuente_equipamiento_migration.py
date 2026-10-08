"""Comprueba la sustitución del esquema financiero ficticio."""

import importlib.util
import unittest
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError


VERSIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _revision(filename: str, operations: Operations):
    spec = importlib.util.spec_from_file_location(filename, VERSIONS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = operations
    return module


class MovimientoFuenteEquipamientoMigrationTestCase(unittest.TestCase):
    def test_descarta_datos_ficticios_y_exige_fuente_en_egresos(self):
        engine = sa.create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            for table in (
                "usuario", "grupo_utn", "fuente_financiamiento",
                "equipamiento_grupo", "memoria_version",
            ):
                connection.exec_driver_sql(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
            connection.exec_driver_sql(
                "CREATE TABLE auditoria_campo (id INTEGER PRIMARY KEY, entidad TEXT NOT NULL)"
            )
            operations = Operations(MigrationContext.configure(connection))
            _revision("e3a7d9b2c4f1_add_movimiento_financiero.py", operations).upgrade()
            connection.exec_driver_sql("INSERT INTO grupo_utn(id) VALUES (1)")
            connection.exec_driver_sql("INSERT INTO fuente_financiamiento(id) VALUES (1)")
            connection.exec_driver_sql("INSERT INTO equipamiento_grupo(id) VALUES (1)")
            connection.exec_driver_sql(
                "INSERT INTO movimiento_financiero "
                "(id, grupo_utn_id, numero_movimiento, fecha, tipo_movimiento, monto, moneda, "
                "categoria_erogacion_id, created_at, activo) "
                "VALUES (1, 1, 1, '2026-09-01', 'EGRESO', 10, 'ARS', 1, '2026-09-01', 1)"
            )
            _revision("f4b8c6d2e9a1_movimientos_fuente_equipamiento.py", operations).upgrade()
            self.assertEqual(connection.exec_driver_sql(
                "SELECT COUNT(*) FROM movimiento_financiero"
            ).scalar_one(), 0)
            columns = {column["name"] for column in sa.inspect(connection).get_columns("movimiento_financiero")}
            self.assertIn("equipamiento_id", columns)
            with self.assertRaises(IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO movimiento_financiero "
                    "(grupo_utn_id, numero_movimiento, fecha, tipo_movimiento, monto, moneda, "
                    "categoria_erogacion_id, created_at, activo) "
                    "VALUES (1, 2, '2026-09-01', 'EGRESO', 10, 'ARS', 1, '2026-09-01', 1)"
                )
            connection.exec_driver_sql(
                "INSERT INTO movimiento_financiero "
                "(grupo_utn_id, numero_movimiento, fecha, tipo_movimiento, monto, moneda, "
                "fuente_financiamiento_id, categoria_erogacion_id, equipamiento_id, created_at, activo) "
                "VALUES (1, 3, '2026-09-01', 'EGRESO', 10, 'ARS', 1, 1, 1, '2026-09-01', 1)"
            )
            with self.assertRaises(IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO movimiento_financiero "
                    "(grupo_utn_id, numero_movimiento, fecha, tipo_movimiento, monto, moneda, "
                    "fuente_financiamiento_id, categoria_erogacion_id, equipamiento_id, created_at, activo) "
                    "VALUES (1, 4, '2026-09-01', 'EGRESO', 10, 'ARS', 1, 1, 1, '2026-09-01', 1)"
                )


if __name__ == "__main__":
    unittest.main()
