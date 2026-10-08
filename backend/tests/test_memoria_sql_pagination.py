import unittest
import re
from datetime import date
from unittest.mock import patch

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.memorias.models.memorias import Memoria
from modules.memorias.services.memoria_service import MemoriaService, SNAPSHOT_ORDERS
from modules.personal.models.personal import PersonalMemoriaVersion


class MemoriaSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all([
            Memoria(periodo_inicio=date(2025, 1, 1), periodo_fin=date(2025, 12, 31))
            for _ in range(12)
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_limita_antes_de_serializar(self):
        statements = []

        def record(_conn, _cursor, statement, _params, _context, _many):
            sql = statement.lower()
            if re.search(r"\bfrom memoria\b", sql) and sql.lstrip().startswith("select"):
                statements.append(sql)

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            with patch.object(MemoriaService, "_serializar_memoria", side_effect=lambda memoria: {"id": memoria.id}) as serialize:
                page, total = MemoriaService.get_page(2, 3)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)

        self.assertEqual(total, 12)
        self.assertEqual([item["id"] for item in page], [9, 8, 7])
        self.assertEqual(serialize.call_count, 3)
        self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))
        self.assertFalse(any("limit" not in sql and "count" not in sql for sql in statements), statements)

    def test_snapshots_de_todas_las_familias_compilan_y_personal_limita_en_sql(self):
        db.session.add_all([
            PersonalMemoriaVersion(
                memoria_version_id=1, personal_id=index,
                tipo_personal_id=1, grupo_utn_id=1,
                nombre_apellido=f"Persona {index:02}",
            ) for index in range(1, 8)
        ])
        db.session.commit()
        statements = []

        def record(_conn, _cursor, statement, _params, _context, _many):
            sql = statement.lower()
            if re.search(r"\bfrom personal_memoria_version\b", sql):
                statements.append(sql)

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            with self.app.test_request_context("/snapshot?page=2&per_page=3"):
                for table_name in SNAPSHOT_ORDERS:
                    result = MemoriaService._snapshot_page_or_none(1, table_name)
                    self.assertIsNone(result["error"])
                    if table_name == "personal_memoria_version":
                        self.assertEqual(result["meta"]["total"], 7)
                        self.assertEqual(
                            [row["nombre_apellido"] for row in result["data"]],
                            ["Persona 04", "Persona 05", "Persona 06"],
                        )
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))


if __name__ == "__main__":
    unittest.main()
