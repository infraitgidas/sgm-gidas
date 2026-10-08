import unittest
from datetime import date, datetime
from types import SimpleNamespace

from modules.memorias.services.memoria_periodo_service import (
    estuvo_activo_en_periodo_memoria,
    fin_vigencia,
    registro_puntual_en_memoria,
    resolver_horas_al_fin,
)


class MemoriaPeriodoServiceTestCase(unittest.TestCase):

    def test_baja_y_fin_funcional_usan_el_primer_limite(self):
        entidad = SimpleNamespace(fecha_fin=date(2027, 1, 1), deleted_at=datetime(2025, 6, 30))
        self.assertEqual(fin_vigencia(entidad), date(2025, 6, 30))
        entidad.fecha_fin = date(2024, 12, 31)
        self.assertEqual(fin_vigencia(entidad), date(2024, 12, 31))

    def test_hecho_puntual_bajas_antes_dentro_y_despues_del_periodo(self):
        version = SimpleNamespace(memoria=SimpleNamespace(periodo_inicio=date(2025, 7, 1), periodo_fin=date(2026, 6, 30)))
        for baja, esperado in ((datetime(2025, 6, 30), False), (datetime(2025, 8, 1), False),
                               (datetime(2026, 2, 1), True), (datetime(2027, 1, 1), True), (None, True)):
            with self.subTest(baja=baja):
                self.assertEqual(registro_puntual_en_memoria(version, SimpleNamespace(deleted_at=baja), date(2026, 1, 1)), esperado)

    def test_horas_usan_fin_y_no_inventan_historial_faltante(self):
        version = SimpleNamespace(memoria=SimpleNamespace(periodo_fin=date(2026, 6, 30)))
        entidad = SimpleNamespace(horas_semanales=40, historial_horas=[
            SimpleNamespace(id=1, horas_semanales=12, fecha_inicio=date(2025, 7, 1), fecha_fin=date(2026, 1, 1)),
            SimpleNamespace(id=2, horas_semanales=24, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 6, 30)),
            SimpleNamespace(id=3, horas_semanales=40, fecha_inicio=date(2026, 7, 1), fecha_fin=None),
        ])
        self.assertEqual(resolver_horas_al_fin(entidad, version), 24)
        version.memoria.periodo_fin = date(2020, 12, 31)
        self.assertIsNone(resolver_horas_al_fin(entidad, version))

    def test_retorna_true_si_estuvo_activo_durante_el_periodo(self):
        memoria_version = SimpleNamespace(
            memoria=SimpleNamespace(
                periodo_inicio=date(2025, 1, 1),
                periodo_fin=date(2025, 12, 31)
            )
        )

        resultado = estuvo_activo_en_periodo_memoria(
            memoria_version,
            fecha_alta=date(2018, 6, 10),
            fecha_baja=datetime(2025, 3, 15, 10, 0, 0)
        )

        self.assertTrue(resultado)

    def test_retorna_false_si_fue_dado_de_baja_antes_del_periodo(self):
        memoria_version = SimpleNamespace(
            memoria=SimpleNamespace(
                periodo_inicio=date(2025, 1, 1),
                periodo_fin=date(2025, 12, 31)
            )
        )

        resultado = estuvo_activo_en_periodo_memoria(
            memoria_version,
            fecha_alta=date(2018, 6, 10),
            fecha_baja=datetime(2024, 12, 31, 23, 59, 59)
        )

        self.assertFalse(resultado)

    def test_retorna_false_si_se_da_de_alta_despues_del_periodo(self):
        memoria_version = SimpleNamespace(
            memoria=SimpleNamespace(
                periodo_inicio=date(2025, 1, 1),
                periodo_fin=date(2025, 12, 31)
            )
        )

        resultado = estuvo_activo_en_periodo_memoria(
            memoria_version,
            fecha_alta=date(2026, 1, 1),
            fecha_baja=None
        )

        self.assertFalse(resultado)


if __name__ == "__main__":
    unittest.main()
