import unittest
from datetime import date, datetime
from unittest.mock import patch

from flask import Flask
from extension import db
from modules import models_registry  # noqa: F401
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.personal.models.tipo_personal import TipoPersonal
from modules.personal.models.personal import Personal, PersonalHorasHistorial, TipoFormacion, TipoDedicacion
from modules.personal.routes.personal_rutas import personal_bp
from modules.personal.services.becario_service import crear_becario
from modules.personal.services.becario_service import actualizar_becario
from modules.personal.services.investigador_service import crear_investigador
from modules.personal.services.investigador_service import actualizar_investigador
from modules.personal.services.personal_service import crear_personal, actualizar_personal
from modules.personal.services.horas_validation import validar_horas_semanales
from modules.personal.services.tipo_personal_service import listar_tipos
from modules.shared.exceptions import ConflictError, ValidationError
from modules.personal.models.personal import Becario, Investigador
from modules.personal.services.personal_completo_service import listar_personal_completo, listar_personal_paginado
from modules.search.services.search_service import SearchService


class PersonalAltaPTAATest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(personal_bp, url_prefix="/api/v1/personal")
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all([
            TipoPersonal(id=1, nombre="Técnico administrativo y de apoyo", activo=True),
            TipoPersonal(id=2, nombre="Profesional", activo=True),
            TipoFormacion(id=1, nombre="Estudiante", activo=True),
            TipoDedicacion(id=1, nombre="Simple", activo=True),
            GrupoInvestigacionUtn(id=1, mail="grupo@example.com", nombre_unidad_academica="UTN",
                                  objetivo_desarrollo="Investigación", nombre_sigla_grupo="Grupo", activo=True),
        ])
        db.session.commit()
        self.client = self.app.test_client()
        self.auth = patch("modules.shared.services.middleware.AuthService.verify_token",
                          return_value={"sub": "1", "rol": "GESTOR"})
        self.auth.start()
        self.addCleanup(self.auth.stop)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def payload(self, **changes):
        return {"nombre_apellido": "Persona PTAA", "dni": "12345678", "cuil": "20-12345678-6", "horas_semanales": 20,
                "tipo_personal_id": 1, "grupo_utn_id": 1,
                "fecha_alta_grupo": "2026-09-01", **changes}

    def post(self, payload):
        return self.client.post("/api/v1/personal", json=payload,
                                headers={"Authorization": "Bearer test"})

    def test_alta_consulta_listado_y_busqueda(self):
        response = self.post(self.payload())
        self.assertEqual(response.status_code, 201)
        record_id = response.get_json()["id"]
        self.assertEqual(response.get_json()["tipo_personal_id"], 1)
        headers = {"Authorization": "Bearer test"}
        detail = self.client.get(f"/api/v1/personal/personal/{record_id}", headers=headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["nombre_apellido"], "Persona PTAA")
        listing = self.client.get("/api/v1/personal", headers=headers)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.get_json()[0]["id"], record_id)
        self.assertEqual(listar_personal_completo(tipo="PTAA")[0]["id"], record_id)
        result = SearchService.search("Persona PTAA")[0]
        self.assertEqual(result["url"], f"/personal/personal/{record_id}")
        self.assertEqual(PersonalHorasHistorial.query.count(), 1)

    def test_dni_unico_entre_variantes_y_edicion_propia(self):
        response = self.post(self.payload())
        self.assertEqual(response.status_code, 201)
        record_id = response.get_json()["id"]
        self.assertEqual(response.get_json()["dni"], "12345678")
        self.assertEqual(response.get_json()["cuil"], "20-12345678-6")

        with self.assertRaisesRegex(ConflictError, "DNI ya esta registrado"):
            crear_becario({**self.payload(), "tipo_formacion_id": 1}, 1)

        own = actualizar_personal(record_id, {"dni": "12345678"}, "personal", 1)
        self.assertEqual(own.identidad.dni, "12345678")
        self.assertEqual(self.post(self.payload()).status_code, 409)

    def test_cuil_formato_digito_y_coincidencia_con_dni(self):
        for cuil in ("20123456786", "20-12345678-7", "20-12345679-4"):
            with self.subTest(cuil=cuil):
                response = self.post(self.payload(cuil=cuil))
                self.assertEqual(response.status_code, 400)
                self.assertIn("cuil", response.get_json()["error"]["details"]["fields"])
        self.assertEqual(Personal.query.count(), 0)

    def test_listado_combina_subtipos_con_altas_recientes_primero(self):
        for id in range(1, 12):
            db.session.add(Personal(id=id, nombre_apellido=f"Personal {id}", horas_semanales=20,
                                    tipo_personal_id=1, grupo_utn_id=1, activo=True,
                                    fecha_alta_grupo=date(2026, 1, 1), created_at=datetime(2026, 9, id)))
        db.session.add_all([
            Becario(id=1, nombre_apellido="Becario reciente", horas_semanales=20, activo=True,
                    tipo_formacion_id=1, grupo_utn_id=1, created_at=datetime(2026, 9, 12)),
            Investigador(id=1, nombre_apellido="Investigador nuevo", horas_semanales=20, activo=True,
                         tipo_dedicacion_id=1, grupo_utn_id=1, created_at=datetime(2026, 9, 13)),
        ])
        db.session.commit()
        listing = listar_personal_completo()
        self.assertEqual([(p["rol"], p["id"]) for p in listing[:3]],
                         [("investigador", 1), ("becario", 1), ("personal", 11)])
        self.assertEqual(listing[:9][0]["nombre_apellido"], "Investigador nuevo")

    def test_listado_paginado_busca_filtra_ordena_y_conserva_contrato_plano(self):
        db.session.add_all([
            Personal(id=20, nombre_apellido="Zulema Tecnica", horas_semanales=30,
                     tipo_personal_id=1, grupo_utn_id=1, activo=True, created_at=datetime(2026, 9, 10)),
            Personal(id=21, nombre_apellido="Ana Administrativa", horas_semanales=10,
                     tipo_personal_id=2, grupo_utn_id=1, activo=False, created_at=datetime(2026, 9, 11)),
            Becario(id=20, nombre_apellido="Becario Visible", horas_semanales=20,
                    tipo_formacion_id=1, grupo_utn_id=1, activo=True, created_at=datetime(2026, 9, 12)),
        ])
        db.session.commit()

        pagina = listar_personal_paginado(page=1, per_page=1, activos="true", sort="nombre", direction="asc")
        self.assertEqual(pagina["meta"]["per_page"], 1)
        self.assertEqual(pagina["meta"]["total_pages"], 2)
        self.assertEqual(pagina["data"][0]["nombre_apellido"], "Becario Visible")
        self.assertEqual(set(pagina["data"][0]), {"id", "rol", "nombre_apellido", "clasificacion", "grupo", "horas_semanales", "activo", "fecha_alta_grupo", "created_at", "updated_at", "deleted_at"})

        filtrada = listar_personal_paginado(page=1, search="zulema", tipo="personal", ids=[20])
        self.assertEqual(filtrada["meta"]["total"], 1)
        self.assertTrue(filtrada["data"][0]["clasificacion"])
        self.assertIsInstance(listar_personal_completo(), list)

        response = self.client.get("/api/v1/personal/all?page=1&per_page=9&tipo=BECARIO",
                                   headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["meta"]["total"], 1)
        self.assertIsNone(response.get_json()["error"])

    def test_listado_paginado_rechaza_parametros_invalidos(self):
        headers = {"Authorization": "Bearer test"}
        for query in ("page=1&per_page=10", "page=0", "page=1&sort=desconocido", "page=1&direction=lateral", "page=1&tipo=otro", "page=1&ids=1,no"):
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/personal/all?{query}", headers=headers)
                self.assertEqual(response.status_code, 400)

    def test_referencia_inexistente_o_inactiva(self):
        for field in ("tipo_personal_id", "grupo_utn_id"):
            with self.subTest(field=field):
                response = self.post(self.payload(**{field: 999}))
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.get_json()["error"]["details"]["fields"])
                self.assertEqual(Personal.query.count(), 0)
        tipo = db.session.get(TipoPersonal, 1)
        tipo.activo = False
        db.session.commit()
        self.assertEqual(self.post(self.payload()).status_code, 400)

    def test_obligatorios_y_horas_enteras(self):
        for field in ("nombre_apellido", "horas_semanales", "tipo_personal_id", "grupo_utn_id", "fecha_alta_grupo"):
            with self.subTest(field=field):
                payload = self.payload()
                del payload[field]
                response = self.post(payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(Personal.query.count(), 0)
        for hours in (True, 1.5, 0):
            self.assertEqual(self.post(self.payload(horas_semanales=hours)).status_code, 400)

    def test_rollback_incluso_si_falla_flush(self):
        original_flush = db.session.flush
        def fail_after_flush(*args, **kwargs):
            original_flush(*args, **kwargs)
            raise RuntimeError("Fallo simulado")
        with patch.object(db.session, "flush", side_effect=fail_after_flush):
            self.assertEqual(self.post(self.payload()).status_code, 500)
        self.assertEqual(Personal.query.count(), 0)
        self.assertEqual(PersonalHorasHistorial.query.count(), 0)
        self.assertEqual(self.post(self.payload()).status_code, 201)

    def test_rollback_si_falla_historial(self):
        with patch("modules.personal.services.personal_service.PersonalHorasHistorial",
                   side_effect=RuntimeError("Fallo simulado")):
            self.assertEqual(self.post(self.payload()).status_code, 500)
        self.assertEqual(Personal.query.count(), 0)
        self.assertEqual(PersonalHorasHistorial.query.count(), 0)

    def test_regresion_profesional_becario_investigador(self):
        self.assertEqual(self.post(self.payload(tipo_personal_id=2)).status_code, 201)
        base = self.payload()
        del base["tipo_personal_id"]
        self.assertIsNotNone(crear_becario({**base, "dni": "12345679", "cuil": "20-12345679-4", "tipo_formacion_id": 1}, 1).id)
        self.assertIsNotNone(crear_investigador({**base, "dni": "12345670", "cuil": "20-12345670-0", "tipo_dedicacion_id": 1}, 1).id)

    def test_lectura_no_puede_crear(self):
        with patch("modules.shared.services.middleware.AuthService.verify_token",
                   return_value={"sub": "1", "rol": "LECTURA"}):
            self.assertEqual(self.post(self.payload()).status_code, 403)
        self.assertEqual(Personal.query.count(), 0)

    def test_limites_horas_en_alta_y_edicion_todas_las_entidades(self):
        base = self.payload()
        cases = [
            (Personal, crear_personal, lambda i, p: actualizar_personal(i, p, "personal", 1), base),
            (Becario, crear_becario, lambda i, p: actualizar_becario(i, p, 1), {**base, "dni": "12345679", "cuil": "20-12345679-4", "tipo_formacion_id": 1}),
            (Investigador, crear_investigador, lambda i, p: actualizar_investigador(i, p, 1), {**base, "dni": "12345670", "cuil": "20-12345670-0", "tipo_dedicacion_id": 1}),
        ]
        for model, create, update, payload in cases:
            with self.subTest(entity=model.__name__):
                for hours in (True, 0, -1, 1.5, 169, 220, "20", None):
                    with self.assertRaises(ValidationError) as error:
                        create({**payload, "horas_semanales": hours}, 1)
                    self.assertIn("horas_semanales", error.exception.details["fields"])
                    self.assertEqual(model.query.count(), 0)
                record = create({**payload, "horas_semanales": 1}, 1)
                for hours in (169, 220, True, 1.5):
                    with self.assertRaises(ValidationError):
                        update(record.id, {"nombre_apellido": "No persistir", "horas_semanales": hours})
                    self.assertEqual(record.horas_semanales, 1)
                    self.assertEqual(record.nombre_apellido, payload["nombre_apellido"])
                    self.assertEqual(len(record.historial_horas), 1)
                update(record.id, {"horas_semanales": 168})
                self.assertEqual(record.horas_semanales, 168)
                self.assertEqual(validar_horas_semanales(168), 168)

    def test_api_rechaza_220_horas_y_acepta_limite_168(self):
        for hours in (169, 220):
            response = self.post(self.payload(horas_semanales=hours))
            self.assertEqual(response.status_code, 400)
            self.assertIn("168", response.get_json()["error"]["details"]["fields"]["horas_semanales"])
        response = self.post(self.payload(horas_semanales=168))
        self.assertEqual(response.status_code, 201)
        record_id = response.get_json()["id"]
        response = self.client.put(f"/api/v1/personal/personal/{record_id}",
                                   json={"horas_semanales": 220}, headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(db.session.get(Personal, record_id).horas_semanales, 168)

    def test_tipo_real_sin_nombre_profesional_prefijado(self):
        tipo = db.session.get(TipoPersonal, 2)
        tipo.nombre = "Especialista de laboratorio"
        db.session.commit()
        response = self.post(self.payload(tipo_personal_id=2))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["tipo_personal_id"], 2)
        tipo.activo = False
        db.session.commit()
        self.assertNotIn(2, [item.id for item in listar_tipos()])
