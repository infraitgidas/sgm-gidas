import unittest
from datetime import date, datetime, timedelta, timezone

import modules.models_registry  # noqa: F401
from modules.recursos.models.equipamiento import Equipamiento
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import serialize_temporal


class DateTimeSerializationTestCase(unittest.TestCase):

    def test_fecha_civil_no_incorpora_zona_horaria(self):
        self.assertEqual(serialize_temporal(date(2026, 1, 1)), "2026-01-01")

    def test_datetime_naive_se_declara_como_utc(self):
        self.assertEqual(
            serialize_temporal(datetime(2026, 9, 7, 2, 13, 31)),
            "2026-09-07T02:13:31Z",
        )

    def test_datetime_con_zona_se_normaliza_a_utc(self):
        argentina = timezone(timedelta(hours=-3))
        self.assertEqual(
            serialize_temporal(datetime(2026, 9, 6, 23, 13, 31, tzinfo=argentina)),
            "2026-09-07T02:13:31Z",
        )

    def test_audit_mixin_distingue_fecha_civil_y_timestamp(self):
        equipo = Equipamiento(
            id=1,
            denominacion="PC",
            descripcion_breve="Equipo",
            fecha_incorporacion=date(2026, 1, 1),
            monto_invertido=1000,
            grupo_utn_id=1,
            created_at=datetime(2026, 9, 7, 2, 13, 31),
        )

        data = equipo.to_dict()

        self.assertEqual(data["fecha_incorporacion"], "2026-01-01")
        self.assertEqual(data["created_at"], "2026-09-07T02:13:31Z")

    def test_historial_serializa_fecha_cambio_como_utc(self):
        item = AuditoriaCampo(
            id=1,
            entidad="equipamiento_grupo",
            registro_id=1,
            campo="fecha_incorporacion",
            fecha_cambio=datetime(2026, 9, 7, 2, 13, 31),
        )

        self.assertEqual(item.serialize()["fecha_cambio"], "2026-09-07T02:13:31Z")

    def test_valor_datetime_de_auditoria_conserva_semantica_utc(self):
        self.assertEqual(
            AuditoriaService._normalizar_valor(datetime(2026, 9, 7, 2, 13, 31)),
            "2026-09-07T02:13:31Z",
        )


if __name__ == "__main__":
    unittest.main()
