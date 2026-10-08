import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app  # noqa: F401 - registra los modelos
from modules.grupo.models.visita_grupo import TipoVisita
from modules.grupo.services.tipo_visita_service import TipoVisitaService
from modules.grupo.services.visita_service import _validar_tipo_visita
from modules.shared.exceptions import ConflictError, ValidationError


class TipoVisitaCatalogTestCase(unittest.TestCase):
    def test_visita_valida_con_catalogo_propio(self):
        tipo = SimpleNamespace(id=7, deleted_at=None)

        with patch(
            "modules.grupo.services.visita_service.db.session.get",
            return_value=tipo,
        ) as get:
            resultado = _validar_tipo_visita(7)

        self.assertEqual(resultado, 7)
        get.assert_called_once_with(TipoVisita, 7)

    def test_visita_rechaza_un_tipo_inactivo(self):
        tipo = SimpleNamespace(id=7, deleted_at=object())

        with patch(
            "modules.grupo.services.visita_service.db.session.get",
            return_value=tipo,
        ), self.assertRaises(ValidationError) as caught:
            _validar_tipo_visita(7)

        self.assertEqual(
            caught.exception.details["fields"],
            {"tipo_visita_id": "Seleccione un tipo de visita disponible."},
        )

    def test_no_permite_eliminar_un_tipo_con_visitas_asociadas(self):
        tipo = SimpleNamespace(visitas=[SimpleNamespace(id=1)])

        with patch.object(TipoVisitaService, "_get_or_404", return_value=tipo), patch(
            "modules.grupo.services.tipo_visita_service.db.session.commit"
        ) as commit, self.assertRaises(ConflictError):
            TipoVisitaService.delete(3, user_id=1)

        commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
