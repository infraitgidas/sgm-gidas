import unittest

from app import create_app  # noqa: F401 - registra los modelos
from modules.shared.exceptions import ValidationError
from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
from modules.personal.services.tipo_personal_service import crear_tipo_personal
from modules.catalogos.services.categoria_utn_service import crear_categoria_utn
from modules.produccion.services.tipo_reunion_service import TipoReunionService
from modules.grupo.services.tipo_visita_service import TipoVisitaService
from modules.recursos.services.becas_service import _validar_nombre_beca


class CatalogNameValidationTestCase(unittest.TestCase):
    def test_rechaza_numeros_y_simbolos_en_los_bordes_publicos(self):
        validators = (
            (lambda value: crear_tipo_personal({"nombre": value}), "nombre"),
            (lambda value: crear_categoria_utn({"nombre": value}), "nombre"),
            (TipoReunionService._validar_nombre, "nombre"),
            (TipoVisitaService._validar_nombre, "nombre"),
            (_validar_nombre_beca, "nombre_beca"),
        )
        for validate, campo in validators:
            for value in ("2026", "# ! / 42"):
                with self.subTest(validate=validate, value=value), self.assertRaises(ValidationError) as caught:
                    validate(value)
                self.assertIn(campo, caught.exception.details["fields"])

    def test_acepta_letras_unicode_con_numeros_y_signos(self):
        for value in ("Tipo 2", "Categoría A-1", "Técnico/Administrativo"):
            validar_nombre_descriptivo(value)


if __name__ == "__main__":
    unittest.main()
