import unittest

from extension import db
from tests import test_personal_alta_ptaa as fixtures
from modules.personal.models.personal import Personal, Becario
from modules.personal.models.tipo_personal import TipoPersonal
from modules.personal.routes.tipo_personal_rutas import tipo_personal_bp
from modules.personal.services.personal_service import crear_personal
from modules.personal.services.reclasificacion_service import reclasificar_personal
from modules.personal.services.tipo_personal_compatibilidad import compatible_con_personal
from modules.shared.models.auditoria_campo import AuditoriaCampo


class PersonalFuncionesClaseTest(unittest.TestCase):
    tearDown = fixtures.PersonalAltaPTAATest.tearDown
    payload = fixtures.PersonalAltaPTAATest.payload
    post = fixtures.PersonalAltaPTAATest.post

    def setUp(self):
        fixtures.PersonalAltaPTAATest.setUp(self)
        self.app.register_blueprint(tipo_personal_bp, url_prefix="/api/v1/tipo-personal")
        db.session.add_all([
            TipoPersonal(id=40, nombre="Docente/investigador", activo=True),
            TipoPersonal(id=41, nombre="Becario", activo=True),
            TipoPersonal(id=42, nombre="Especialista de laboratorio", activo=True),
        ])
        db.session.commit()
        self.headers = {"Authorization": "Bearer test"}

    def test_regla_sin_ids_fijos_y_catalogo_con_compatibilidad(self):
        for nombre in ("Docente/investigador", "DOCENTE - INVESTIGADOR", "Personal docente", "Investigadora", "Becaria"):
            with self.subTest(nombre=nombre):
                self.assertFalse(compatible_con_personal(nombre))
        for nombre in ("Técnico", "Administrativo", "De Apoyo", "Profesional", "Especialista de laboratorio", "Apoyo a investigación"):
            self.assertTrue(compatible_con_personal(nombre))
        response = self.client.get("/api/v1/tipo-personal/", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        tipos = {row["id"]: row for row in response.get_json()}
        self.assertFalse(tipos[40]["compatible_con_personal"])
        self.assertFalse(tipos[41]["compatible_con_personal"])
        self.assertTrue(tipos[42]["compatible_con_personal"])
        # El catálogo administrativo conserva las opciones y la paginación.
        response = self.client.get("/api/v1/tipo-personal/?page=1&per_page=9", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all("compatible_con_personal" in row for row in response.get_json()["data"]))

    def test_alta_rechaza_funcion_incompatible_y_admite_personalizada(self):
        for tipo_id in (40, 41):
            response = self.post(self.payload(tipo_personal_id=tipo_id))
            self.assertEqual(response.status_code, 400)
            self.assertIn("tipo_personal_id", response.get_json()["error"]["details"]["fields"])
            self.assertEqual(Personal.query.count(), 0)
        self.assertEqual(self.post(self.payload(tipo_personal_id=42)).status_code, 201)

    def test_edicion_rechaza_sin_mutar_campos_identidad_ni_auditoria(self):
        persona = crear_personal(self.payload(), 1)
        for tipo_id in (40, 41):
            response = self.client.put(f"/api/v1/personal/personal/{persona.id}",
                json={"tipo_personal_id": tipo_id, "nombre": "Otro", "horas_semanales": 30}, headers=self.headers)
            self.assertEqual(response.status_code, 400)
            db.session.expire_all()
            self.assertEqual(persona.nombre, "Persona")
            self.assertEqual(persona.tipo_personal_id, 1)
            self.assertEqual(persona.horas_semanales, 20)
            self.assertEqual(AuditoriaCampo.query.count(), 0)
        response = self.client.put(f"/api/v1/personal/personal/{persona.id}", json={"tipo_personal_id": 42}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(persona.tipo_personal_id, 42)
        self.assertEqual(AuditoriaCampo.query.filter_by(campo="tipo_personal_id").count(), 1)

    def test_reclasificacion_reutiliza_regla_y_conserva_origen_al_rechazar(self):
        persona = crear_personal(self.payload(), 1)
        becario = reclasificar_personal("personal", persona.id, {"clase_destino": "becario", "tipo_formacion_id": 1}, 1)
        for tipo_id in (40, 41):
            response = self.client.put(f"/api/v1/personal/becario/{becario['id']}/reclasificar",
                json={"clase_destino": "personal", "tipo_personal_id": tipo_id}, headers=self.headers)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(Personal.query.count(), 0)
            self.assertEqual(Becario.query.count(), 1)
        result = reclasificar_personal("becario", becario["id"], {"clase_destino": "personal", "tipo_personal_id": 42}, 1)
        self.assertEqual(result["tipo_personal_id"], 42)
        self.assertEqual(result["identidad_id"], becario["identidad_id"])

    def test_catalogo_no_puede_introducir_incompatibilidad_por_renombrado(self):
        persona = crear_personal(self.payload(), 1)
        response = self.client.put("/api/v1/tipo-personal/1", json={"nombre": "Investigador"}, headers=self.headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(persona.tipo_personal.nombre, "Técnico administrativo y de apoyo")

    def test_asignacion_heredada_requiere_corregir_funcion_sin_reescribir_historico(self):
        persona = crear_personal(self.payload(), 1)
        persona.tipo_personal_id = 40
        db.session.commit()
        response = self.client.put(f"/api/v1/personal/personal/{persona.id}", json={"horas_semanales": 30}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("tipo_personal_id", response.get_json()["error"]["details"]["fields"])
        self.assertEqual(persona.tipo_personal_id, 40)
        self.assertEqual(persona.horas_semanales, 20)
        self.assertEqual(AuditoriaCampo.query.count(), 0)
