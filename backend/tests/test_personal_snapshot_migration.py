import importlib.util
from pathlib import Path
import unittest

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


spec = importlib.util.spec_from_file_location("snapshot_identidad_revision", Path(__file__).resolve().parents[1] / "migrations/versions/e4a6c8f0b2d3_personal_snapshot_identidad.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class PersonalSnapshotMigrationTest(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.connection.close)
        self.connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self.connection.exec_driver_sql("CREATE TABLE identidad_personal (id INTEGER PRIMARY KEY)")
        self.connection.exec_driver_sql("INSERT INTO identidad_personal VALUES (7)")
        for clase in migration.CLASES:
            self.connection.exec_driver_sql(f"CREATE TABLE {clase} (id INTEGER PRIMARY KEY, identidad_id INTEGER REFERENCES identidad_personal(id))")
            self.connection.exec_driver_sql(f"INSERT INTO {clase} VALUES (1, 7), (2, NULL)")
            self.connection.exec_driver_sql(f"CREATE TABLE {clase}_memoria_version (id INTEGER PRIMARY KEY, memoria_version_id INTEGER NOT NULL, {clase}_id INTEGER NOT NULL REFERENCES {clase}(id), nombre_apellido VARCHAR(120) NOT NULL, UNIQUE (memoria_version_id, {clase}_id))")
            self.connection.exec_driver_sql(f"INSERT INTO {clase}_memoria_version VALUES (10, 1, 1, 'Nombre histórico'), (11, 1, 2, 'Nombre heredado')")

    def run_revision(self, action):
        with Operations.context(MigrationContext.configure(self.connection)):
            action()

    def test_backfill_conserva_fotos_y_permite_eliminar_clase_sin_eliminar_identidad(self):
        self.run_revision(migration.upgrade)
        for clase in migration.CLASES:
            tabla = f"{clase}_memoria_version"
            rows = self.connection.execute(sa.text(f"SELECT id, memoria_version_id, {clase}_id, nombre_apellido, identidad_id FROM {tabla} ORDER BY id")).all()
            self.assertEqual(rows, [(10, 1, 1, "Nombre histórico", 7), (11, 1, 2, "Nombre heredado", None)])
            self.connection.exec_driver_sql(f"DELETE FROM {clase} WHERE id=1")
            self.assertEqual(self.connection.exec_driver_sql(f"SELECT nombre_apellido FROM {tabla} WHERE id=10").scalar(), "Nombre histórico")
            fks = sa.inspect(self.connection).get_foreign_keys(tabla)
            self.assertEqual([fk["referred_table"] for fk in fks], ["identidad_personal"])
        with self.assertRaises(sa.exc.IntegrityError), self.connection.begin_nested():
            self.connection.exec_driver_sql("DELETE FROM identidad_personal WHERE id=7")
        with self.assertRaisesRegex(RuntimeError, "No se puede revertir"):
            self.run_revision(migration.downgrade)
        # El rechazo sucede antes de modificar cualquiera de las tres tablas.
        for clase in migration.CLASES:
            self.assertIn("identidad_id", [col["name"] for col in sa.inspect(self.connection).get_columns(f"{clase}_memoria_version")])

    def test_downgrade_antes_de_reclasificar_conserva_referencias_originales(self):
        self.run_revision(migration.upgrade)
        self.run_revision(migration.downgrade)
        for clase in migration.CLASES:
            tabla = f"{clase}_memoria_version"
            self.assertNotIn("identidad_id", [col["name"] for col in sa.inspect(self.connection).get_columns(tabla)])
            self.assertEqual(sa.inspect(self.connection).get_foreign_keys(tabla)[0]["referred_table"], clase)

    def test_no_admite_dos_fotos_de_una_identidad_en_la_misma_clase_y_version(self):
        self.run_revision(migration.upgrade)
        with self.assertRaises(sa.exc.IntegrityError), self.connection.begin_nested():
            self.connection.exec_driver_sql("INSERT INTO personal_memoria_version VALUES (12, 1, 99, 'Duplicado', 7)")
