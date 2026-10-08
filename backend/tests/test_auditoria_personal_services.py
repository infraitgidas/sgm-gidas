import unittest
from unittest.mock import patch
from types import SimpleNamespace

from modules.personal.models.personal import Personal, Becario, Investigador
from modules.personal.services.becario_service import actualizar_becario
from modules.personal.services.investigador_service import actualizar_investigador
from modules.personal.services.personal_service import actualizar_personal


class AuditoriaPersonalServicesTestCase(unittest.TestCase):

    def setUp(self):
        self.commit_patcher = patch("extension.db.session.commit")
        self.rollback_patcher = patch("extension.db.session.rollback")
        self.add_patcher = patch("extension.db.session.add")

        self.mock_commit = self.commit_patcher.start()
        self.mock_rollback = self.rollback_patcher.start()
        self.mock_add = self.add_patcher.start()

        self.addCleanup(self.commit_patcher.stop)
        self.addCleanup(self.rollback_patcher.stop)
        self.addCleanup(self.add_patcher.stop)

    def test_actualizar_investigador_registra_auditoria(self):
        investigador = Investigador(
            id=1,
            nombre_apellido="Ana Perez",
            horas_semanales=10,
            tipo_dedicacion_id=1,
            categoria_utn_id=2,
            programa_incentivos_id=3,
            grupo_utn_id=4,
            created_by=1
        )
        investigador.deleted_at = None
        investigador.updated_at = None
        investigador.updated_by = None

        with patch(
            "modules.personal.services.investigador_service._obtener_investigador_activo",
            return_value=investigador
        ), patch(
            "modules.personal.services.investigador_service._validar_tipo_dedicacion",
            return_value=5
        ), patch(
            "modules.personal.services.investigador_service._validar_grupo_utn",
            return_value=6
        ), patch(
            "modules.personal.services.investigador_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            resultado = actualizar_investigador(
                1,
                {
                    "nombre_apellido": "Ana Gomez",
                    "tipo_dedicacion_id": 5,
                    "grupo_utn_id": 6
                },
                user_id=25
            )

        self.assertEqual(resultado.nombre_apellido, "Ana Gomez")
        self.assertEqual(resultado.tipo_dedicacion_id, 5)
        self.assertEqual(resultado.grupo_utn_id, 6)
        self.assertEqual(resultado.updated_by, 25)
        self.assertIsNotNone(resultado.updated_at)
        mock_registrar.assert_called_once()

    def test_actualizar_becario_registra_auditoria(self):
        becario = Becario(
            id=2,
            nombre_apellido="Luis Diaz",
            horas_semanales=12,
            tipo_formacion_id=1,
            grupo_utn_id=2,
            created_by=1
        )
        becario.deleted_at = None
        becario.updated_at = None
        becario.updated_by = None

        with patch(
            "modules.personal.services.becario_service._get_activo_or_404",
            return_value=becario
        ), patch(
            "modules.personal.services.becario_service.TipoFormacion",
            new=SimpleNamespace(query=SimpleNamespace(get=lambda _: object()))
        ), patch(
            "modules.personal.services.becario_service.GrupoInvestigacionUtn",
            new=SimpleNamespace(query=SimpleNamespace(get=lambda _: object()))
        ), patch(
            "modules.personal.services.becario_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            resultado = actualizar_becario(
                2,
                {
                    "nombre_apellido": "Luis Fernandez",
                    "tipo_formacion_id": 3,
                    "grupo_utn_id": 4
                },
                user_id=30
            )

        self.assertEqual(resultado.nombre_apellido, "Luis Fernandez")
        self.assertEqual(resultado.tipo_formacion_id, 3)
        self.assertEqual(resultado.grupo_utn_id, 4)
        self.assertEqual(resultado.updated_by, 30)
        self.assertIsNotNone(resultado.updated_at)
        mock_registrar.assert_called_once()

    def test_actualizar_personal_registra_auditoria(self):
        personal = Personal(
            id=3,
            nombre_apellido="Maria Lopez",
            horas_semanales=20,
            tipo_personal_id=1,
            grupo_utn_id=2,
            created_by=1
        )
        personal.deleted_at = None
        personal.updated_at = None
        personal.updated_by = None

        with patch(
            "modules.personal.services.personal_service._resolver_entidad_por_rol",
            return_value=(personal, object(), "personal_id")
        ), patch(
            "modules.personal.services.personal_service._validar_tipo_personal",
            return_value=5
        ), patch(
            "modules.personal.services.personal_service._validar_grupo_utn",
            return_value=6
        ), patch(
            "modules.personal.services.personal_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            resultado = actualizar_personal(
                3,
                {
                    "nombre_apellido": "Maria Suarez",
                    "tipo_personal_id": 5,
                    "grupo_utn_id": 6
                },
                "personal",
                user_id=40
            )

        self.assertEqual(resultado.nombre_apellido, "Maria Suarez")
        self.assertEqual(resultado.tipo_personal_id, 5)
        self.assertEqual(resultado.grupo_utn_id, 6)
        self.assertEqual(resultado.updated_by, 40)
        self.assertIsNotNone(resultado.updated_at)
        mock_registrar.assert_called_once()

    def test_actualizar_investigador_no_audita_si_no_hay_cambios(self):
        investigador = Investigador(
            id=4,
            nombre_apellido="Carla Ruiz",
            horas_semanales=15,
            tipo_dedicacion_id=2,
            categoria_utn_id=None,
            programa_incentivos_id=None,
            grupo_utn_id=8,
            created_by=1
        )
        investigador.deleted_at = None
        investigador.updated_at = None
        investigador.updated_by = None

        with patch(
            "modules.personal.services.investigador_service._obtener_investigador_activo",
            return_value=investigador
        ), patch(
            "modules.personal.services.investigador_service._validar_grupo_utn",
            return_value=8
        ), patch(
            "modules.personal.services.investigador_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            actualizar_investigador(
                4,
                {
                    "nombre_apellido": "Carla Ruiz",
                    "grupo_utn_id": 8
                },
                user_id=11
            )

        self.assertIsNone(investigador.updated_at)
        self.assertIsNone(investigador.updated_by)
        mock_registrar.assert_not_called()

    def test_actualizar_investigador_permite_quitar_categoria_y_programa(self):
        investigador = Investigador(id=5, nombre_apellido="Laura Ruiz", horas_semanales=15,
                                    tipo_dedicacion_id=2, categoria_utn_id=7,
                                    programa_incentivos_id=8, grupo_utn_id=9, created_by=1)
        investigador.deleted_at = None
        with patch("modules.personal.services.investigador_service._obtener_investigador_activo", return_value=investigador), patch(
            "modules.personal.services.investigador_service.AuditoriaService.registrar_cambios"
        ) as registrar:
            actualizar_investigador(5, {"categoria_utn_id": None, "programa_incentivos_id": None}, user_id=2)

        self.assertIsNone(investigador.categoria_utn_id)
        self.assertIsNone(investigador.programa_incentivos_id)
        cambios = registrar.call_args.kwargs["cambios"]
        self.assertEqual(set(cambios), {"categoria_utn_id", "programa_incentivos_id"})

    def test_actualizar_investigador_rechaza_catalogos_invalidos(self):
        investigador = Investigador(id=6, nombre_apellido="Laura Ruiz", horas_semanales=15,
                                    tipo_dedicacion_id=2, grupo_utn_id=9, created_by=1)
        investigador.deleted_at = None
        with patch("modules.personal.services.investigador_service._obtener_investigador_activo", return_value=investigador), patch(
            "modules.personal.services.investigador_service.CategoriaUtn",
            new=SimpleNamespace(query=SimpleNamespace(get=lambda _: None))
        ), self.assertRaises(Exception):
            actualizar_investigador(6, {"categoria_utn_id": 999}, user_id=2)


if __name__ == "__main__":
    unittest.main()
