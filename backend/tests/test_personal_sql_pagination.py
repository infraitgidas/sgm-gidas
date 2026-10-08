import re
import unittest

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.personal.models.personal import Becario, Investigador, Personal, TipoDedicacion, TipoFormacion
from modules.personal.models.tipo_personal import TipoPersonal
from modules.personal.services.becario_service import listar_becarios_paginado
from modules.personal.services.investigador_service import listar_investigadores_paginado
from modules.personal.services.personal_service import listar_personal_pagina
from modules.personal.services.tipo_dedicacion_service import listar_tipos_dedicacion_paginado
from modules.personal.services.tipo_formacion_service import listar_tipos_formacion_paginado
from modules.personal.services.tipo_personal_service import listar_tipos_paginado


class PersonalSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all([
            GrupoInvestigacionUtn(id=1, mail="uct@example.test", nombre_unidad_academica="Regional",
                                  objetivo_desarrollo="Investigacion", nombre_sigla_grupo="UCT"),
            TipoPersonal(id=1, nombre="Tecnico"),
            TipoFormacion(id=1, nombre="Grado"),
        ])
        db.session.flush()
        for index in range(12):
            db.session.add_all([
                Personal(nombre_apellido=f"Personal {index:02}", horas_semanales=10,
                         tipo_personal_id=1, grupo_utn_id=1),
                Becario(nombre_apellido=f"Becario {index:02}", horas_semanales=10,
                        tipo_formacion_id=1, grupo_utn_id=1),
                Investigador(nombre_apellido=f"Investigador {index:02}", horas_semanales=10,
                             grupo_utn_id=1),
            ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_tres_subtipos_limitados_en_sql(self):
        for table, service in (
            ("personal", listar_personal_pagina),
            ("becario", listar_becarios_paginado),
            ("investigador", listar_investigadores_paginado),
        ):
            statements = []

            def record(_conn, _cursor, statement, _params, _context, _many):
                sql = statement.lower()
                if re.search(rf"\bfrom {table}\b", sql):
                    statements.append(sql)

            event.listen(db.engine, "before_cursor_execute", record)
            try:
                rows, total = service(2, 3)
            finally:
                event.remove(db.engine, "before_cursor_execute", record)

            self.assertEqual(total, 12)
            self.assertEqual(len(rows), 3)
            self.assertEqual([row.id for row in rows], [4, 5, 6])
            self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))
            self.assertFalse(any("limit" not in sql and "count" not in sql for sql in statements))

    def test_catalogos_de_personal_limitados_en_sql(self):
        db.session.add(TipoDedicacion(nombre="Dedicacion 01"))
        db.session.add_all([
            item
            for index in range(2, 13)
            for item in (
                TipoPersonal(nombre=f"Personal {index:02}"),
                TipoFormacion(nombre=f"Formacion {index:02}"),
                TipoDedicacion(nombre=f"Dedicacion {index:02}"),
            )
        ])
        db.session.commit()
        for table, service in (
            ("tipo_personal", listar_tipos_paginado),
            ("tipo_formacion_becario", listar_tipos_formacion_paginado),
            ("tipo_dedicacion", listar_tipos_dedicacion_paginado),
        ):
            statements = []

            def record(_conn, _cursor, statement, _params, _context, _many):
                sql = statement.lower()
                if re.search(rf"\bfrom {table}\b", sql):
                    statements.append(sql)

            event.listen(db.engine, "before_cursor_execute", record)
            try:
                rows, total = service(2, 3)
            finally:
                event.remove(db.engine, "before_cursor_execute", record)
            self.assertEqual((len(rows), total), (3, 12))
            self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))


if __name__ == "__main__":
    unittest.main()
