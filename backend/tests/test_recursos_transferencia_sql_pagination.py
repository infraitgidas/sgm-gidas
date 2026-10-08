import re
import unittest

from flask import Flask
from sqlalchemy import event

from extension import db
from modules import models_registry  # noqa: F401
from modules.recursos.models.becas import Beca
from modules.recursos.services.becas_service import BecaService
from modules.recursos.services.equipamiento_service import EquipamientoService
from modules.recursos.services.movimiento_financiero_service import MovimientoFinancieroService
from modules.recursos.services.tipo_erogacion_service import TipoErogacionService
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.transferencia.models.transferencia_socio import Adoptante, TipoContrato
from modules.transferencia.services.adoptante_service import AdoptanteService
from modules.transferencia.services.tipo_contrato_service import TipoContratoService
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService


class RecursosTransferenciaSqlPaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all([
            item
            for index in range(12)
            for item in (
                Adoptante(nombre=f"Adoptante {index:02}"),
                TipoContrato(nombre=f"Contrato {index:02}"),
                Beca(nombre_beca=f"Beca {index:02}"),
            )
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_consultas_paginadas_antes_de_serializar(self):
        cases = (
            ("adoptante", lambda: AdoptanteService.get_page(2, 3), 12),
            ("tipo_contrato_transferencia", lambda: TipoContratoService.get_page(2, 3), 12),
            ("beca", lambda: BecaService.get_page(2, 3), 12),
            ("equipamiento_grupo", lambda: EquipamientoService.get_page(2, 3), 0),
            ("movimiento_financiero", lambda: MovimientoFinancieroService.get_page({}, 2, 3), 0),
            ("transferencia_socio_productiva", lambda: TransferenciaSocioProductivaService.get_page({}, 2, 3), 0),
        )
        for table, fetch, expected_total in cases:
            statements = []

            def record(_conn, _cursor, statement, _params, _context, _many):
                sql = statement.lower()
                if re.search(rf"\bfrom {table}\b", sql):
                    statements.append(sql)

            event.listen(db.engine, "before_cursor_execute", record)
            try:
                rows, total = fetch()
            finally:
                event.remove(db.engine, "before_cursor_execute", record)
            self.assertEqual(total, expected_total, table)
            self.assertEqual(len(rows), 3 if expected_total else 0, table)
            self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements), table)

    def test_colecciones_secundarias_limitadas_en_sql(self):
        db.session.add(GrupoInvestigacionUtn(
            id=1, mail="uct@example.com", nombre_unidad_academica="UTN",
            objetivo_desarrollo="Objetivo", nombre_sigla_grupo="UCT",
        ))
        db.session.commit()
        for fetch in (
            lambda: BecaService.get_becas_activas_en_anio(2026, 2, 3),
            lambda: BecaService.get_becarios_de_beca(Beca.query.first().id, 2, 3),
            lambda: MovimientoFinancieroService.equipamientos_disponibles(1, page=2, per_page=3),
            lambda: TipoErogacionService.get_page(2, 3),
        ):
            statements = []

            def record(_conn, _cursor, sql, _params, _context, _many):
                if sql.lstrip().lower().startswith("select"):
                    statements.append(sql.lower())

            event.listen(db.engine, "before_cursor_execute", record)
            try:
                data, total = fetch()
            finally:
                event.remove(db.engine, "before_cursor_execute", record)
            self.assertEqual((data, total), ([], 0))
            self.assertTrue(any("limit" in sql and "offset" in sql for sql in statements))


if __name__ == "__main__":
    unittest.main()
