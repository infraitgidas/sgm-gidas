import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import sqlalchemy as sa


path = Path(__file__).resolve().parents[1] / "migrations/versions/d3f5a7c9e1b2_normalizar_nombres_personal.py"
spec = importlib.util.spec_from_file_location("personal_names_migration", path)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class PersonalNamesMigrationTest(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.metadata = sa.MetaData()
        self.tables = {}
        for name in migration.TABLAS:
            self.tables[name] = sa.Table(name, self.metadata,
                sa.Column("id", sa.Integer, primary_key=True), sa.Column("nombre_apellido", sa.String),
                sa.Column("nombre", sa.String), sa.Column("apellido", sa.String), sa.Column("grupo_utn_id", sa.Integer))
        self.audit = sa.Table("auditoria_campo", self.metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("entidad", sa.String),
            sa.Column("registro_id", sa.Integer), sa.Column("campo", sa.String),
            sa.Column("valor_anterior", sa.JSON), sa.Column("valor_nuevo", sa.JSON), sa.Column("fecha_cambio", sa.DateTime))
        self.metadata.create_all(self.engine)
        self.connection = self.engine.connect()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.connection.close)

    def run_migration(self):
        with patch.object(migration.op, "get_bind", return_value=self.connection):
            migration.upgrade()

    def test_revisa_todas_las_filas_antes_de_modificar_y_rechaza_desconocidos(self):
        self.connection.execute(self.tables["personal"].insert(), {"id": 1, "nombre_apellido": "Carla Ruiz"})
        self.connection.execute(self.tables["becario"].insert(), {"id": 2, "nombre_apellido": "Desconocido Sin Mapeo"})
        with self.assertRaisesRegex(RuntimeError, "migracion cancelada"):
            self.run_migration()
        self.assertIsNone(self.connection.execute(sa.select(self.tables["personal"].c.nombre)).scalar())
        self.assertEqual(self.connection.execute(sa.select(sa.func.count()).select_from(self.audit)).scalar(), 0)

    def test_normaliza_tres_clases_preserva_relaciones_y_audita_originales(self):
        examples = (("personal", "Tecnico Administrativo 01 TEST", "Tomás", "García"),
                    ("becario", "Lic. Bruno Gomez", "Bruno", "Gomez"),
                    ("investigador", "Lautaro Di Lollo", "Lautaro", "Di Lollo"))
        for table, original, _, _ in examples:
            self.connection.execute(self.tables[table].insert(), {"id": 7, "nombre_apellido": original, "grupo_utn_id": 99})
        self.run_migration()
        for table, original, nombre, apellido in examples:
            row = self.connection.execute(sa.select(self.tables[table])).mappings().one()
            self.assertEqual((row["id"], row["grupo_utn_id"], row["nombre"], row["apellido"]), (7, 99, nombre, apellido))
            audits = self.connection.execute(sa.select(self.audit).where(self.audit.c.entidad == table)).mappings().all()
            if original != row["nombre_apellido"]:
                self.assertTrue(any(item["campo"] == "nombre_apellido" and item["valor_anterior"] == original for item in audits))
        count = self.connection.execute(sa.select(sa.func.count()).select_from(self.audit)).scalar()
        self.run_migration()
        self.assertEqual(self.connection.execute(sa.select(sa.func.count()).select_from(self.audit)).scalar(), count)

    def test_no_sobrescribe_nombres_estructurados_y_rechaza_parciales_incompatibles(self):
        table = self.tables["personal"]
        self.connection.execute(table.insert(), {"id": 1, "nombre_apellido": "Ana del Valle", "nombre": "Ana", "apellido": "del Valle"})
        self.run_migration()
        self.assertEqual(self.connection.execute(sa.select(table.c.apellido)).scalar(), "del Valle")
        self.connection.execute(table.insert(), {"id": 2, "nombre_apellido": "Carla Ruiz", "nombre": "Otra"})
        with self.assertRaisesRegex(RuntimeError, "incompatible"):
            self.run_migration()

    def test_todas_las_correspondencias_son_nombres_validos(self):
        for original, (nombre, apellido) in migration.NOMBRES.items():
            with self.subTest(original=original):
                self.assertTrue(nombre and apellido)
                self.assertTrue(all(part.isalpha() for part in (nombre + " " + apellido).split()))
                self.assertLessEqual(max(len(nombre), len(apellido)), 60)
