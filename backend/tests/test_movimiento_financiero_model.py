import unittest
from decimal import Decimal

from modules import models_registry  # noqa: F401
from modules.recursos.models.movimiento_financiero import MovimientoFinanciero
from modules.shared.exceptions import ValidationError


class MovimientoFinancieroModelTestCase(unittest.TestCase):
    def test_acepta_unico_monto_decimal_y_tipo_valido(self):
        movimiento = MovimientoFinanciero(
            grupo_utn_id=1,
            numero_movimiento=1,
            tipo_movimiento="INGRESO",
            monto="1234.50",
            moneda="ARS",
        )

        self.assertEqual(movimiento.monto, Decimal("1234.50"))
        self.assertEqual(movimiento.tipo_movimiento, "INGRESO")
        self.assertNotIn("ingresos", MovimientoFinanciero.__table__.columns)
        self.assertNotIn("egresos", MovimientoFinanciero.__table__.columns)

    def test_rechaza_montos_no_positivos_y_no_finitos(self):
        for monto in (0, "-0.01", "NaN", "Infinity", "1.001", None, True):
            with self.subTest(monto=monto), self.assertRaises(ValidationError):
                MovimientoFinanciero(monto=monto)

    def test_rechaza_tipo_moneda_y_numero_invalidos(self):
        for values in (
            {"tipo_movimiento": "TRANSFERENCIA"},
            {"moneda": "EUR"},
            {"numero_movimiento": 0},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                MovimientoFinanciero(**values)


if __name__ == "__main__":
    unittest.main()
