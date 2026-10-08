import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.recursos.services.becas_service import BecaService


class BecaHistorialTestCase(unittest.TestCase):

    def test_obtener_historial_beca_retorna_auditoria_ordenada(self):
        auditoria = AuditoriaCampo(
            id=1,
            entidad="beca",
            registro_id=3,
            campo="nombre_beca",
            valor_anterior="Beca Inicial",
            valor_nuevo="Beca Actualizada",
            fecha_cambio=datetime(2026, 4, 25, 10, 0, 0),
            usuario_id=9
        )
        auditoria.usuario = SimpleNamespace(nombre_usuario="admin")

        fake_query = SimpleNamespace(
            filter=lambda *args, **kwargs: SimpleNamespace(
                order_by=lambda *a, **k: SimpleNamespace(all=lambda: [auditoria])
            )
        )

        with patch(
            "modules.recursos.services.becas_service._get_beca_or_404",
            return_value=SimpleNamespace(id=3)
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
            historial = BecaService.get_historial(3)

        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["campo"], "nombre_beca")
        self.assertEqual(historial[0]["usuario_nombre"], "admin")


if __name__ == "__main__":
    unittest.main()
