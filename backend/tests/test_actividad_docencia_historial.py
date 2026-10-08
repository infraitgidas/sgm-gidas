import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.produccion.models.actividad_docencia import ActividadDocencia, InvestigadorActividadGrado
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.produccion.services.actividad_docencia_service import ActividadDocenciaService


class ActividadDocenciaHistorialTestCase(unittest.TestCase):

    def test_serialize_actividad_normaliza_historial_grados(self):
        actividad = ActividadDocencia(
            id=1,
            curso="Curso A",
            institucion="UTN",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 7, 1),
            investigador_id=2,
            rol_actividad_id=3,
            created_by=1
        )
        actividad.__dict__["investigador"] = SimpleNamespace(
            id=2,
            nombre_apellido="Ana Perez",
            deleted_at=None
        )
        actividad.__dict__["rol_actividad"] = SimpleNamespace(id=3, nombre="Titular")

        historial_activo = InvestigadorActividadGrado(
            id=11,
            investigador_id=2,
            actividad_docencia_id=1,
            grado_academico_id=5,
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=None,
            created_by=1
        )
        historial_activo.__dict__["grado_academico"] = SimpleNamespace(id=5, nombre="Grado A")
        historial_activo.created_by_user = None
        historial_activo.updated_by_user = None
        historial_activo.deleted_by_user = None

        historial_anterior = InvestigadorActividadGrado(
            id=10,
            investigador_id=2,
            actividad_docencia_id=1,
            grado_academico_id=4,
            fecha_inicio=date(2024, 1, 1),
            fecha_fin=date(2024, 2, 28),
            created_by=1
        )
        historial_anterior.__dict__["grado_academico"] = SimpleNamespace(id=4, nombre="Grado B")
        historial_anterior.created_by_user = None
        historial_anterior.updated_by_user = None
        historial_anterior.deleted_by_user = None

        actividad.__dict__["investigadores_grado"] = [historial_anterior, historial_activo]
        actividad.created_by_user = None
        actividad.updated_by_user = None
        actividad.deleted_by_user = None

        resultado = actividad.serialize()

        self.assertEqual(resultado["investigador"]["id"], 2)
        self.assertEqual(resultado["grado_academico_actual"]["id"], 5)
        self.assertEqual(len(resultado["historial_grados"]), 2)
        self.assertEqual(resultado["historial_grados"][0]["id"], 11)
        self.assertTrue(resultado["historial_grados"][0]["activo"])
        self.assertEqual(
            resultado["historial_grados"][0]["grado_academico"]["nombre"],
            "Grado A"
        )

    def test_get_historial_integra_historial_grados(self):
        actividad = SimpleNamespace(
            id=1,
            investigadores_grado=[
                SimpleNamespace(
                    id=1,
                    fecha_inicio=date(2024, 1, 1),
                    fecha_fin=date(2024, 2, 1),
                    grado_academico=SimpleNamespace(id=7, nombre="Asistente"),
                    created_by=2,
                    created_by_user=SimpleNamespace(nombre_usuario="gestor"),
                    serialize=lambda: {"id": 1, "grado_academico": {"id": 7}}
                ),
                SimpleNamespace(
                    id=2,
                    fecha_inicio=date(2024, 3, 1),
                    fecha_fin=None,
                    grado_academico=SimpleNamespace(id=8, nombre="Titular"),
                    created_by=3,
                    created_by_user=SimpleNamespace(nombre_usuario="admin"),
                    serialize=lambda: {"id": 2, "grado_academico": {"id": 8}}
                )
            ]
        )

        with patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaService._obtener_actividad",
            return_value=actividad
        ), patch(
            "modules.produccion.services.actividad_docencia_service.AuditoriaService.obtener_historial_entidad",
            return_value=[
                {
                    "id": 9,
                    "campo": "curso",
                    "fecha_cambio": "2026-04-23T10:00:00",
                    "valor_anterior": "A",
                    "valor_nuevo": "B"
                },
                {
                    "id": 10,
                    "campo": "grado_academico_id",
                    "fecha_cambio": "2026-04-23T09:00:00",
                    "valor_anterior": 7,
                    "valor_nuevo": 8
                }
            ]
        ):
            resultado = ActividadDocenciaService.get_historial(1)

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]["campo"], "curso")
        self.assertEqual(resultado[1]["tipo"], "historial_grado")
        self.assertEqual(resultado[1]["valor_nuevo"]["id"], 8)
        self.assertEqual(resultado[1]["valor_anterior"]["id"], 7)

    def test_historial_grados_no_interpreta_el_alta_como_cambio(self):
        actividad = SimpleNamespace(
            id=1,
            investigadores_grado=[
                SimpleNamespace(
                    id=1,
                    fecha_inicio=date(2024, 1, 1),
                    fecha_fin=None,
                    grado_academico=SimpleNamespace(id=7, nombre="Asistente"),
                    created_by=2,
                    created_by_user=SimpleNamespace(nombre_usuario="gestor"),
                    serialize=lambda: {"id": 1, "grado_academico": {"id": 7}},
                )
            ],
        )

        resultado = ActividadDocenciaService._construir_historial_grados(actividad)

        self.assertEqual(resultado, [])

    def test_get_historial_devuelve_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="actividad_y_catedra_posgrado",
            registro_id=1,
            campo="curso",
            valor_anterior="Curso A",
            valor_nuevo="Curso B",
            fecha_cambio=datetime(2026, 4, 23, 10, 0, 0),
            usuario_id=3
        )
        auditoria.usuario = SimpleNamespace(nombre_usuario="admin")

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [auditoria])
            )
        )

        with patch(
            "modules.produccion.services.actividad_docencia_service.ActividadDocenciaService._obtener_actividad",
            return_value=SimpleNamespace(id=1, investigadores_grado=[])
        ), patch(
            "modules.shared.services.auditoria_service.AuditoriaCampo",
            new=SimpleNamespace(
                query=fake_query,
                entidad=None,
                registro_id=None,
                fecha_cambio=SimpleNamespace(desc=lambda: None),
                id=SimpleNamespace(desc=lambda: None)
            )
        ):
            historial = ActividadDocenciaService.get_historial(1)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "curso")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")
