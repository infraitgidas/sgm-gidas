import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from flask import Flask

from extension import db
from modules import models_registry  # noqa: F401
from modules.shared.exceptions import NotFoundError, ValidationError
from modules.shared.models.form_draft import FormDraft
from modules.shared.services.form_draft_service import FormDraftService


class FormDraftServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_unico_borrador_por_usuario_formulario_y_registro(self):
        FormDraftService.save(1, "proyectos", "new", {"nombreProyecto": "Uno"})
        FormDraftService.save(1, "proyectos", "new", {"nombreProyecto": "Dos"})
        FormDraftService.save(1, "recursos-erogaciones", "new", {"fecha": "2026-09-17"})
        FormDraftService.save(2, "proyectos", "new", {"nombreProyecto": "Otro"})

        self.assertEqual(FormDraft.query.count(), 3)
        self.assertEqual(len(FormDraftService.list_for_user(1)), 2)
        self.assertEqual(FormDraftService.get(1, "proyectos", "new")["data"], {"nombreProyecto": "Dos"})
        self.assertEqual(FormDraftService.get(2, "proyectos", "new")["data"], {"nombreProyecto": "Otro"})
        FormDraftService.delete(1, "proyectos", "new")
        with self.assertRaises(NotFoundError):
            FormDraftService.get(1, "proyectos", "new")
        self.assertEqual(FormDraft.query.count(), 2)

    def test_rechaza_secretos_y_payload_excesivo_sin_persistir(self):
        for data in ({"password": "secreto"}, {"nested": [{"accessToken": "secreto"}]}, {"texto": "a" * 65537}):
            with self.subTest(data=list(data)):
                with self.assertRaises(ValidationError):
                    FormDraftService.save(1, "proyectos", "new", data)
        self.assertEqual(FormDraft.query.count(), 0)

    def test_vencimiento_oculta_borrador(self):
        FormDraftService.save(1, "proyectos", "new", {"nombreProyecto": "Viejo"})
        row = FormDraft.query.one()
        row.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()
        self.assertEqual(FormDraftService.list_for_user(1), [])
        self.assertEqual(FormDraft.query.count(), 0)
        with self.assertRaises(NotFoundError):
            FormDraftService.get(1, "proyectos", "new")

    def test_lista_identifica_personal_por_nombre_sin_exponer_campos(self):
        FormDraftService.save(1, "personal-investigador", "29", {
            "__draft_meta": {"schema": 1, "base_fingerprint": "abc"},
            "fields": {"nombreApellido": "  Benjamín   Pérez  ", "horasSemanales": 20},
        })
        FormDraftService.save(1, "personal-becario", "31", {"nombreApellido": "Persona 22"})
        summaries = FormDraftService.list_for_user(1)
        investigator = next(row for row in summaries if row["module"] == "personal-investigador")
        fellow = next(row for row in summaries if row["module"] == "personal-becario")
        self.assertEqual(investigator["display_name"], "Benjamín Pérez")
        self.assertNotIn("data", investigator)
        self.assertNotIn("display_name", fellow)

    def test_lista_identifica_borradores_de_otros_modulos(self):
        examples = (
            ("recursos-erogaciones", {"numeroErogacion": "142"}, "142"),
            ("recursos-equipamiento", {"denominacion": "Microscopio"}, "Microscopio"),
            ("proyectos", {"nombreProyecto": "Proyecto Delta"}, "Proyecto Delta"),
            ("transferencia", {"data": {"denominacion": "Convenio Norte"}}, "Convenio Norte"),
            ("produccion-documentacion", {"data": {"titulo": "Informe anual"}}, "Informe anual"),
            ("grupo-uct", {"data": {"nombreSigla": "GIDAS"}}, "GIDAS"),
        )
        for module, fields, expected in examples:
            with self.subTest(module=module):
                FormDraftService.save(1, module, "new", {
                    "__draft_meta": {"schema": 1, "base_fingerprint": "abc"},
                    "fields": fields,
                })
                summary = next(row for row in FormDraftService.list_for_user(1) if row["module"] == module)
                self.assertEqual(summary["display_name"], expected)
                self.assertNotIn("data", summary)

    def test_borrador_de_proyecto_en_edicion_abre_ruta_canonica(self):
        FormDraftService.save(1, "proyectos", "42", {"nombreProyecto": "Proyecto Delta"})
        summary = FormDraftService.list_for_user(1)[0]
        self.assertEqual(summary["path"], "/proyectos/42/editar")


class FormDraftRouteTestCase(unittest.TestCase):
    def setUp(self):
        from app import create_app
        with patch("app.register_tenant_request_scope"):
            self.app = create_app()
        self.client = self.app.test_client()

    def test_roles_y_auth_protegen_borradores(self):
        path = "/api/v1/borradores"
        self.assertEqual(self.client.get(path).status_code, 401)
        with patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "1", "rol": "LECTURA"}):
            self.assertEqual(self.client.get(path, headers={"Authorization": "Bearer test"}).status_code, 403)

    def test_contrato_autenticado_aisla_usuario_y_desactiva_cache(self):
        headers = {"Authorization": "Bearer test"}
        identity = {"sub": "7", "rol": "GESTOR"}
        with patch("modules.shared.services.middleware.AuthService.verify_token", return_value=identity), \
             patch.object(FormDraftService, "save", return_value={"module": "proyectos", "record_key": "new"}) as save, \
             patch.object(FormDraftService, "get", return_value={"data": {"nombreProyecto": "Prueba"}}) as get, \
             patch.object(FormDraftService, "list_for_user", return_value=[]) as list_all, \
             patch.object(FormDraftService, "delete") as delete:
            response = self.client.put("/api/v1/borradores/proyectos/new", headers=headers, json={"data": {"nombreProyecto": "Prueba"}})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Cache-Control"], "private, no-store")
            save.assert_called_once_with(7, "proyectos", "new", {"nombreProyecto": "Prueba"})
            self.assertEqual(self.client.get("/api/v1/borradores/proyectos/new", headers=headers).status_code, 200)
            get.assert_called_once_with(7, "proyectos", "new")
            self.assertEqual(self.client.get("/api/v1/borradores", headers=headers).status_code, 200)
            list_all.assert_called_once_with(7)
            self.assertEqual(self.client.delete("/api/v1/borradores/proyectos/new", headers=headers).status_code, 200)
            delete.assert_called_once_with(7, "proyectos", "new")


if __name__ == "__main__":
    unittest.main()
