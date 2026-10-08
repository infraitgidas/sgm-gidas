import unittest
from unittest.mock import Mock, patch

from modules.produccion.services.documentacion_service import DocumentacionBibliograficaService


class DocumentacionAutoresHistorialTest(unittest.TestCase):
    def test_vincular_y_desvincular_registra_eventos_con_snapshot(self):
        doc = Mock(id=5, autores=[])
        autor = Mock(id=9, nombre_apellido="Ana Pérez", deleted_at=None)
        with patch.object(DocumentacionBibliograficaService, "_get_activo_or_404", return_value=doc), \
             patch("modules.produccion.services.documentacion_service.db.session.get", return_value=autor), \
             patch("modules.produccion.services.documentacion_service.db.session.commit") as commit, \
             patch("modules.produccion.services.documentacion_service.AuditoriaService.registrar_evento_relacion") as audit:
            DocumentacionBibliograficaService.add_autor(5, 9, 17)
            self.assertIn(autor, doc.autores)
            self.assertEqual(audit.call_args.kwargs["accion"], "vincular")
            self.assertEqual(audit.call_args.kwargs["detalle"], {"nombre_apellido": "Ana Pérez"})
            self.assertEqual(audit.call_args.kwargs["user_id"], 17)
            DocumentacionBibliograficaService.remove_autor(5, 9, 18)
            self.assertNotIn(autor, doc.autores)
            self.assertEqual(audit.call_args.kwargs["accion"], "desvincular")
            self.assertEqual(audit.call_args.kwargs["detalle"], {"nombre_apellido": "Ana Pérez"})
            self.assertEqual(commit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
