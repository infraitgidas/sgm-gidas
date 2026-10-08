from datetime import date, timedelta
import unittest

from modules.shared.exceptions import ValidationError
from modules.shared.services.date_time import validate_institutional_date


class InstitutionalDateValidationTestCase(unittest.TestCase):
    def test_rechaza_fecha_anterior_a_creacion_del_grupo(self):
        with self.assertRaisesRegex(ValidationError, "posterior al 01/01/2010"):
            validate_institutional_date(date(2009, 12, 31), "fecha")

    def test_acepta_inicio_del_rango_institucional(self):
        value = date(2010, 1, 1)
        self.assertEqual(validate_institutional_date(value, "fecha"), value)

    def test_permita_futuro_solo_si_el_modulo_lo_admite(self):
        future = date.today() + timedelta(days=1)
        self.assertEqual(validate_institutional_date(future, "fecha"), future)

        with self.assertRaisesRegex(ValidationError, "no puede ser futuro"):
            validate_institutional_date(future, "fecha", allow_future=False)


if __name__ == "__main__":
    unittest.main()
