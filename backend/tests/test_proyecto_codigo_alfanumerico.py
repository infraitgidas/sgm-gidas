import importlib
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from modules.proyectos.models.proyecto_investigacion import (
    ProyectoInvestigacion,
    ProyectoInvestigacionMemoriaVersion,
)
from modules.produccion.models.distinciones import DistincionRecibidaMemoriaVersion
from modules.proyectos.services.proyecto_investigacion_service import (
    ProyectoInvestigacionService,
)
from modules.shared.exceptions import ValidationError


class ProyectoCodigoAlfanumericoTestCase(unittest.TestCase):
    def test_modelos_persisten_codigo_como_string_de_50_caracteres(self):
        columnas = (
            ProyectoInvestigacion.__table__.c.codigo_proyecto,
            ProyectoInvestigacionMemoriaVersion.__table__.c.codigo_proyecto,
            DistincionRecibidaMemoriaVersion.__table__.c.proyecto_codigo,
        )

        for columna in columnas:
            with self.subTest(columna=columna.name):
                self.assertIsInstance(columna.type, sa.String)
                self.assertEqual(columna.type.length, 50)

    def test_create_acepta_recorta_y_conserva_codigo_alfanumerico(self):
        proyecto = SimpleNamespace(
            serialize=lambda: {"codigo_proyecto": "LPSIEC1347"}
        )
        data = {
            "codigo_proyecto": "  LPSIEC1347  ",
            "nombre_proyecto": "SAVIA",
            "descripcion_proyecto": "Descripción",
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-12-31",
            "tipo_proyecto_id": 1,
        }

        with patch(
            "modules.proyectos.services.proyecto_investigacion_service.TipoProyecto"
        ) as tipo_model, patch(
            "modules.proyectos.services.proyecto_investigacion_service.ProyectoInvestigacion",
            return_value=proyecto,
        ) as proyecto_model, patch(
            "modules.proyectos.services.proyecto_investigacion_service.db.session.add"
        ), patch(
            "modules.proyectos.services.proyecto_investigacion_service.db.session.commit"
        ):
            tipo_model.query.get.return_value = object()
            resultado = ProyectoInvestigacionService.create(data, user_id=7)

        self.assertEqual(resultado["codigo_proyecto"], "LPSIEC1347")
        self.assertEqual(
            proyecto_model.call_args.kwargs["codigo_proyecto"],
            "LPSIEC1347",
        )

    def test_update_valida_y_conserva_case_del_codigo(self):
        proyecto = SimpleNamespace(
            id=4,
            codigo_proyecto="1001",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=None,
            serialize=lambda: {"codigo_proyecto": proyecto.codigo_proyecto},
        )
        query = SimpleNamespace(
            filter_by=lambda **_: SimpleNamespace(first=lambda: proyecto)
        )

        with patch(
            "modules.proyectos.services.proyecto_investigacion_service.ProyectoInvestigacion",
            new=SimpleNamespace(query=query),
        ), patch(
            "modules.proyectos.services.proyecto_investigacion_service.db.session.commit"
        ):
            resultado = ProyectoInvestigacionService.update(
                4,
                {"codigo_proyecto": "AbC123"},
            )

        self.assertEqual(resultado["codigo_proyecto"], "AbC123")

    def test_create_y_update_rechazan_codigo_invalido_con_error_de_campo(self):
        with self.assertRaises(ValidationError) as create_error:
            ProyectoInvestigacionService.create(
                {"codigo_proyecto": "LPS-1347"},
                user_id=7,
            )

        self.assertIn(
            "codigo_proyecto",
            create_error.exception.details["fields"],
        )

        proyecto = SimpleNamespace(id=4)
        query = SimpleNamespace(
            filter_by=lambda **_: SimpleNamespace(first=lambda: proyecto)
        )
        with patch(
            "modules.proyectos.services.proyecto_investigacion_service.ProyectoInvestigacion",
            new=SimpleNamespace(query=query),
        ), self.assertRaises(ValidationError) as update_error:
            ProyectoInvestigacionService.update(
                4,
                {"codigo_proyecto": " "},
            )

        self.assertEqual(
            update_error.exception.details["fields"]["codigo_proyecto"],
            "El código del proyecto es obligatorio.",
        )


class ProyectoCodigoMigrationTestCase(unittest.TestCase):
    def test_upgrade_preserva_numericos_y_downgrade_rechaza_alfanumericos(self):
        migration = importlib.import_module(
            "migrations.versions.c6e8a1f4b2d9_change_project_codes_to_string"
        )
        engine = sa.create_engine("sqlite://")

        with engine.begin() as connection:
            connection.execute(sa.text(
                "CREATE TABLE proyecto_investigacion "
                "(id INTEGER PRIMARY KEY, codigo_proyecto INTEGER NOT NULL)"
            ))
            connection.execute(sa.text(
                "CREATE TABLE proyecto_investigacion_memoria_version "
                "(id INTEGER PRIMARY KEY, codigo_proyecto INTEGER NOT NULL)"
            ))
            connection.execute(sa.text(
                "CREATE TABLE distincion_recibida_memoria_version "
                "(id INTEGER PRIMARY KEY, proyecto_codigo INTEGER NULL)"
            ))
            connection.execute(sa.text(
                "INSERT INTO proyecto_investigacion VALUES (1, 1001)"
            ))
            connection.execute(sa.text(
                "INSERT INTO proyecto_investigacion_memoria_version VALUES (1, 1001)"
            ))
            connection.execute(sa.text(
                "INSERT INTO distincion_recibida_memoria_version VALUES (1, 1001)"
            ))

            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, "op", operations):
                migration.upgrade()

                valor = connection.execute(sa.text(
                    "SELECT codigo_proyecto FROM proyecto_investigacion WHERE id = 1"
                )).scalar_one()
                self.assertEqual(valor, "1001")

                connection.execute(sa.text(
                    "UPDATE proyecto_investigacion "
                    "SET codigo_proyecto = 'LPSIEC1347' WHERE id = 1"
                ))
                with self.assertRaisesRegex(RuntimeError, "No se puede revertir"):
                    migration.downgrade()

                connection.execute(sa.text(
                    "UPDATE proyecto_investigacion "
                    "SET codigo_proyecto = '1001' WHERE id = 1"
                ))
                migration.downgrade()

            tipo_final = sa.inspect(connection).get_columns(
                "proyecto_investigacion"
            )[1]["type"]
            self.assertIsInstance(tipo_final, sa.Integer)


if __name__ == "__main__":
    unittest.main()
