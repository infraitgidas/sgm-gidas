"""Prueba optativa con rol migrador en un schema efímero, sin datos de aplicación."""
import os
import unittest
import uuid

import sqlalchemy as sa
from tests import test_personal_snapshot_migration as fixtures


@unittest.skipUnless(os.getenv("ISS38_POSTGRES_TEST") == "1", "Requiere ejecución explícita con rol migrador")
class PersonalSnapshotPostgresTest(fixtures.PersonalSnapshotMigrationTest):
    def setUp(self):
        url = os.environ["DATABASE_URL"]
        self.schema = "iss38_test_" + uuid.uuid4().hex
        self.admin = sa.create_engine(url)
        with self.admin.begin() as conn:
            conn.exec_driver_sql(f"CREATE SCHEMA {self.schema}")
        self.addCleanup(self.drop_schema)
        self.engine = sa.create_engine(url, connect_args={"options": f"-c search_path={self.schema}"})
        self.connection = self.engine.connect()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.connection.close)
        self.connection.exec_driver_sql("CREATE TABLE identidad_personal (id INTEGER PRIMARY KEY)")
        self.connection.exec_driver_sql("INSERT INTO identidad_personal VALUES (7)")
        for clase in fixtures.migration.CLASES:
            self.connection.exec_driver_sql(f"CREATE TABLE {clase} (id INTEGER PRIMARY KEY, identidad_id INTEGER REFERENCES identidad_personal(id))")
            self.connection.exec_driver_sql(f"INSERT INTO {clase} VALUES (1, 7), (2, NULL)")
            self.connection.exec_driver_sql(f"CREATE TABLE {clase}_memoria_version (id INTEGER PRIMARY KEY, memoria_version_id INTEGER NOT NULL, {clase}_id INTEGER NOT NULL REFERENCES {clase}(id), nombre_apellido VARCHAR(120) NOT NULL, UNIQUE (memoria_version_id, {clase}_id))")
            self.connection.exec_driver_sql(f"INSERT INTO {clase}_memoria_version VALUES (10, 1, 1, 'Nombre histórico'), (11, 1, 2, 'Nombre heredado')")

    def drop_schema(self):
        # El nombre solo se construye con un prefijo fijo y uuid hexadecimal.
        with self.admin.begin() as conn:
            conn.exec_driver_sql(f"DROP SCHEMA {self.schema} CASCADE")
        self.admin.dispose()
