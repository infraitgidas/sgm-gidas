import importlib.util
import unittest
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "d5a7e9c1b3f2_audit_bibliographic_authors.py"


class AutoresBibliograficosMigrationTest(unittest.TestCase):
    def test_migracion_conserva_autores_existentes_y_permite_reversion(self):
        spec = importlib.util.spec_from_file_location("audit_bibliographic_authors", MIGRATION)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        sa.Table("usuario", metadata, sa.Column("id", sa.Integer, primary_key=True))
        sa.Table("grupo_utn", metadata, sa.Column("id", sa.Integer, primary_key=True))
        autor = sa.Table(
            "autor", metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("grupo_utn_id", sa.Integer, sa.ForeignKey("grupo_utn.id")),
            sa.Column("nombre_apellido", sa.Text, nullable=False),
        )
        sa.Table("autorxlibro", metadata, sa.Column("id_autor", sa.Integer, sa.ForeignKey("autor.id"), primary_key=True))

        with engine.begin() as connection:
            metadata.create_all(connection)
            connection.execute(sa.text("INSERT INTO grupo_utn (id) VALUES (1)"))
            connection.execute(autor.insert().values(id=7, grupo_utn_id=1, nombre_apellido="Ana Pérez"))
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration.upgrade()

            columns = {column["name"] for column in sa.inspect(connection).get_columns("autor")}
            self.assertTrue({"created_at", "updated_at", "deleted_at", "activo", "created_by", "updated_by", "deleted_by"} <= columns)
            row = connection.execute(sa.text("SELECT nombre_apellido, created_at, activo FROM autor WHERE id = 7")).one()
            self.assertEqual(row.nombre_apellido, "Ana Pérez")
            self.assertIsNotNone(row.created_at)
            self.assertEqual(row.activo, 1)

            with Operations.context(context):
                migration.downgrade()
            columns = {column["name"] for column in sa.inspect(connection).get_columns("autor")}
            self.assertNotIn("deleted_at", columns)
            self.assertEqual(connection.execute(sa.text("SELECT nombre_apellido FROM autor WHERE id = 7")).scalar_one(), "Ana Pérez")


if __name__ == "__main__":
    unittest.main()
