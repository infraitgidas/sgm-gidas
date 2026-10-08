import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from modules.produccion.models.actividad_docencia import ActividadDocencia
from modules.produccion.models.documentacion_autores import DocumentacionBibliografica
from modules.proyectos.models.participacion_relevante import ParticipacionRelevante
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion
from modules.produccion.services.actividad_docencia_service import ActividadDocenciaService
from modules.produccion.services.documentacion_service import DocumentacionBibliograficaService
from modules.proyectos.services.participacion_relevante_service import ParticipacionRelevanteService
from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService


class AuditoriaTanda2ServicesTestCase(unittest.TestCase):

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

    def test_update_proyecto_registra_auditoria(self):
        proyecto = ProyectoInvestigacion(
            id=1,
            codigo_proyecto=100,
            nombre_proyecto="Proyecto A",
            descripcion_proyecto="Descripcion inicial",
            fecha_inicio=date(2024, 1, 1),
            fecha_fin=None,
            dificultades_proyecto="Ninguna",
            monto_destinado=1000,
            tipo_proyecto_id=1,
            grupo_utn_id=2,
            fuente_financiamiento_id=3,
            created_by=1
        )
        proyecto.deleted_at = None
        proyecto.updated_at = None
        proyecto.updated_by = None

        fake_query = SimpleNamespace(
            filter_by=lambda **kwargs: SimpleNamespace(first=lambda: proyecto)
        )

        with patch(
            "modules.proyectos.services.proyecto_investigacion_service.ProyectoInvestigacion",
            new=SimpleNamespace(query=fake_query)
        ), patch(
            "modules.proyectos.services.proyecto_investigacion_service.TipoProyecto",
            new=SimpleNamespace(query=SimpleNamespace(get=lambda _: object()))
        ), patch(
            "modules.proyectos.services.proyecto_investigacion_service.GrupoInvestigacionUtn",
            new=SimpleNamespace(query=SimpleNamespace(get=lambda _: object()))
        ), patch(
            "modules.proyectos.services.proyecto_investigacion_service.FuenteFinanciamiento",
            new=SimpleNamespace(query=SimpleNamespace(get=lambda _: object()))
        ), patch(
            "modules.proyectos.services.proyecto_investigacion_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            resultado = ProyectoInvestigacionService.update(
                1,
                {
                    "nombre_proyecto": "Proyecto B",
                    "monto_destinado": 2500,
                    "tipo_proyecto_id": 5
                },
                user_id=10
            )

        self.assertEqual(resultado["nombre_proyecto"], "Proyecto B")
        self.assertEqual(resultado["monto_destinado"], 2500)
        self.assertEqual(resultado["tipo_proyecto_id"], 5)
        self.assertEqual(proyecto.updated_by, 10)
        self.assertIsNotNone(proyecto.updated_at)
        mock_registrar.assert_called_once()

    def test_update_actividad_docencia_registra_auditoria(self):
        actividad = ActividadDocencia(
            id=2,
            curso="Curso inicial",
            institucion="UTN",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 6, 1),
            rol_actividad_id=1,
            investigador_id=7,
            created_by=1
        )
        actividad.deleted_at = None
        actividad.updated_at = None
        actividad.updated_by = None
        historial = SimpleNamespace(grado_academico_id=2, fecha_inicio=date(2024, 3, 1))

        with patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaService._obtener_actividad",
            return_value=actividad
        ), patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaService._validar_rol",
            return_value=SimpleNamespace(id=3)
        ), patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaService._validar_grado",
            return_value=SimpleNamespace(id=4)
        ), patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaService._obtener_historial_activo_unico",
            return_value=historial
        ), patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaService._validar_no_duplicado"
        ), patch(
            "modules.produccion.services.actividad_docencia_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            resultado = ActividadDocenciaService.update(
                2,
                {
                    "curso": "Curso actualizado",
                    "rol_actividad_id": 3,
                    "grado_academico_id": 4
                },
                user_id=12
            )

        self.assertEqual(resultado["curso"], "Curso actualizado")
        self.assertEqual(resultado["rol_actividad_id"], 3)
        self.assertEqual(actividad.updated_by, 12)
        self.assertIsNotNone(actividad.updated_at)
        mock_registrar.assert_called_once()

    def test_update_participacion_relevante_registra_auditoria(self):
        part = ParticipacionRelevante(
            id=3,
            nombre_evento="evento a",
            forma_participacion="panelista",
            fecha=date(2024, 4, 5),
            investigador_id=9,
            created_by=1
        )
        part.deleted_at = None
        part.updated_at = None
        part.updated_by = None

        with patch(
            "modules.proyectos.services.participacion_relevante_service.ParticipacionRelevanteService._get_activa_or_404",
            return_value=part
        ), patch(
            "modules.proyectos.services.participacion_relevante_service.ParticipacionRelevanteService._validar_no_duplicado"
        ), patch(
            "modules.proyectos.services.participacion_relevante_service.ParticipacionRelevanteService._validar_participante",
            return_value=("investigador", 11, SimpleNamespace(nombre_apellido="Investigador B"))
        ), patch(
            "modules.proyectos.services.participacion_relevante_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            resultado = ParticipacionRelevanteService.update(
                3,
                {
                    "nombre_evento": "Evento B",
                    "participante": {"rol": "investigador", "id": 11}
                },
                user_id=15
            )

        self.assertEqual(resultado["nombre_evento"], "evento b")
        self.assertEqual(resultado["investigador_id"], 11)
        self.assertEqual(part.updated_by, 15)
        self.assertIsNotNone(part.updated_at)
        mock_registrar.assert_called_once()

    def test_update_documentacion_registra_auditoria(self):
        doc = DocumentacionBibliografica(
            id=4,
            titulo="titulo inicial",
            editorial="editorial inicial",
            anio=2022,
            grupo_id=1,
            created_by=1
        )
        doc.deleted_at = None
        doc.updated_at = None
        doc.updated_by = None

        with patch(
            "modules.produccion.services.documentacion_service.DocumentacionBibliograficaService._get_activo_or_404",
            return_value=doc
        ), patch(
            "modules.produccion.services.documentacion_service.AuditoriaService.registrar_cambios"
        ) as mock_registrar:
            resultado = DocumentacionBibliograficaService.update(
                4,
                {
                    "titulo": "Titulo nuevo",
                    "anio": 2025
                },
                user_id=18
            )

        self.assertEqual(resultado["titulo"], "titulo nuevo")
        self.assertEqual(resultado["anio"], 2025)
        self.assertEqual(doc.updated_by, 18)
        self.assertIsNotNone(doc.updated_at)
        mock_registrar.assert_called_once()


if __name__ == "__main__":
    unittest.main()
