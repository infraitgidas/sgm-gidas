from datetime import date
import unittest

from extension import db
from modules.auth.models.usuario import Usuario
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.memorias.models.memorias import Memoria
from modules.memorias.services.memoria_service import MemoriaService
from modules.memorias.services.exportacion_service_impl import ExportService
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion
from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService
from tests import test_memoria_2025_seed as seed_fixtures
from tools.seed_memoria_validacion import populate, DATES


class MemoriaSeedValidacionTest(unittest.TestCase):
    setUp = seed_fixtures.Memoria2025SeedTest.setUp
    cleanup = seed_fixtures.Memoria2025SeedTest.cleanup

    def seed(self):
        group = GrupoInvestigacionUtn(nombre_sigla_grupo="GIDAS", nombre_unidad_academica="La Plata",
                                     mail="gidas@frlp.utn.edu.ar", objetivo_desarrollo="Investigación aplicada")
        db.session.add(group)
        db.session.commit()
        self.group_id = group.id
        return populate(group.id, self.admin.id)

    def snapshot(self, start, end):
        memoria = MemoriaService.create({"grupo_utn_id": self.group_id, "periodo_inicio": str(start), "periodo_fin": str(end)}, self.admin.id)
        MemoriaService.change_status(memoria["id"], {"estado": "cerrada"}, self.admin.id)
        model = db.session.get(Memoria, memoria["id"])
        return ExportService._build_memoria_snapshot_sources(model.id, model.version_actual_id)

    def test_carga_formal_idempotente_sin_memorias_y_plazos_validos(self):
        credentials = {user.id: user.contrasena for user in Usuario.query.all()}
        result = self.seed()
        self.assertEqual(Memoria.query.count(), 0)
        self.assertEqual(result["creados"]["becario"], 30)
        self.assertEqual(result["creados"]["personal"], 10)
        self.assertEqual(result["creados"]["transferencia_socio_productiva"], 48)
        self.assertEqual(result["creados"]["trabajo_reunion_cientifica"], 16)
        self.assertEqual(result["creados"]["trabajos_revista"], 16)
        for project in ProyectoInvestigacion.query.all():
            ProyectoInvestigacionService._validar_duracion(project.fecha_inicio, project.fecha_fin)
            self.assertEqual(project.fecha_fin_original, project.fecha_fin)
        self.assertEqual(credentials, {user.id: user.contrasena for user in Usuario.query.all()})
        self.assertFalse(populate(self.group_id, self.admin.id)["created"])
        for table in db.metadata.tables.values():
            for row in db.session.execute(table.select()).mappings():
                for value in row.values():
                    if isinstance(value, str):
                        self.assertNotIn("TEST", value.upper())

    def test_snapshot_periodo_parcial_excluye_hechos_y_conserva_vigencias_2025(self):
        self.seed()
        sources = self.snapshot(date(2026, 1, 1), date(2026, 3, 31))
        self.assertEqual(len(sources["trabajos_reunion"]), 4)
        self.assertEqual(len(sources["articulos"]), 2)
        self.assertEqual(len(sources["documentacion"]), 2)
        self.assertEqual(len(sources["erogaciones"]), 6)
        self.assertTrue(any(str(item["fecha_inicio"]).startswith("2025") for item in sources["proyectos"]))
        self.assertTrue(any(str(item["fecha_incorporacion"]).startswith("2025") for item in sources["equipamiento"]))
        self.assertTrue(all(str(item["fecha_publicacion"]).startswith("2026") for item in sources["articulos"]))
        self.assertTrue(all(str(item["fecha_presentacion"]) <= "2026-03-31" for item in sources["trabajos_reunion"]))

    def test_reemplazo_elimina_memoria_2026_y_preserva_credenciales_otra_uct(self):
        self.seed()
        self.snapshot(date(2026, 1, 1), DATES[-1])
        other = GrupoInvestigacionUtn(nombre_sigla_grupo="OTRA", nombre_unidad_academica="Otra Facultad",
            mail="otra@utn.edu.ar", objetivo_desarrollo="Investigación")
        db.session.add(other)
        db.session.commit()
        result = populate(self.group_id, self.admin.id, replace=True)
        self.assertEqual(result["eliminados"]["memoria"], 1)
        self.assertEqual(Memoria.query.count(), 0)
        self.assertIsNotNone(db.session.get(GrupoInvestigacionUtn, other.id))
        self.assertEqual(len(self.snapshot(date(2026, 1, 1), DATES[-1])["trabajos_reunion"]), 12)

    def test_retirar_proyecto_2026_no_modifica_la_foto_de_memoria_2024(self):
        self.seed()
        example = ProyectoInvestigacion.query.first()
        payload = {"codigo_proyecto": "GIDAS202401", "nombre_proyecto": "Plataforma institucional de análisis",
            "descripcion_proyecto": "Investigación sobre interoperabilidad de plataformas académicas.",
            "fecha_inicio": "2024-01-01", "fecha_fin": "2026-12-31", "grupo_utn_id": self.group_id,
            "tipo_proyecto_id": example.tipo_proyecto_id, "fuente_financiamiento_id": example.fuente_financiamiento_id}
        project = ProyectoInvestigacionService.create(payload, self.admin.id)
        historical = self.snapshot(date(2024, 1, 1), date(2024, 12, 31))
        original = historical["proyectos"]
        result = populate(self.group_id, self.admin.id, replace=True)
        self.assertEqual(result["archivados_para_preservar_historia"]["proyecto_investigacion"], [project["id"]])
        actual = ExportService._build_memoria_snapshot_sources(historical["memoria"].id, historical["version"].id)
        self.assertEqual(actual["proyectos"], original)
        sources = self.snapshot(date(2026, 1, 1), DATES[-1])
        self.assertNotIn("GIDAS202401", [item["codigo_proyecto"] for item in sources["proyectos"]])


if __name__ == "__main__":
    unittest.main()
