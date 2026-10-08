import unittest
from datetime import date

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.grupo.models.directivos import Cargo, Directivo, DirectivoGrupo
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.grupo.services.directivo_service import DirectivoGrupoService


class DirectivoSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add(GrupoInvestigacionUtn(
            id=1, mail="uct@example.com", nombre_unidad_academica="UTN",
            objetivo_desarrollo="Objetivo", nombre_sigla_grupo="UCT",
        ))
        db.session.add(Cargo(id=1, nombre="Director"))
        db.session.add_all(Directivo(id=index, nombre_apellido=f"Directivo {index:02}", grupo_utn_id=1)
                           for index in range(1, 8))
        db.session.flush()
        db.session.add_all(DirectivoGrupo(
            id=index, id_directivo=index, id_grupo_utn=1, id_cargo=1,
            fecha_inicio=date(2020 + index, 1, 1),
        ) for index in range(1, 8))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_paginas_directivos_y_mandatos(self):
        statements = []

        def record(_conn, _cursor, sql, _params, _context, _many):
            if "from directivo" in sql.lower():
                statements.append(sql.lower())

        event.listen(db.engine, "before_cursor_execute", record)
        try:
            all_rows, all_total = DirectivoGrupoService.get_all_page(2, 3)
            group_rows, group_total = DirectivoGrupoService.get_por_grupo(1, 2, 3)
            current_rows, current_total = DirectivoGrupoService.get_actuales_por_grupo(1, 2, 3)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertEqual((all_total, group_total, current_total), (7, 7, 7))
        self.assertEqual(len(all_rows), 3)
        self.assertEqual([row["id"] for row in group_rows], [4, 3, 2])
        self.assertEqual(len(current_rows), 3)
        self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))


if __name__ == "__main__":
    unittest.main()
