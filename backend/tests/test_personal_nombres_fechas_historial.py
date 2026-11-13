import unittest
from datetime import date, timedelta

from extension import db
from tests import test_personal_alta_ptaa as fixtures
from modules.personal.services.personal_service import crear_personal, actualizar_personal, obtener_historial_personal_por_rol
from modules.personal.services.becario_service import crear_becario, actualizar_becario
from modules.personal.services.investigador_service import crear_investigador, actualizar_investigador
from modules.personal.services.nombre_service import nombre_para_memoria
from modules.personal.services.fecha_validation import validar_fecha_alta_grupo
from modules.shared.exceptions import ValidationError
from modules.shared.models.auditoria_campo import AuditoriaCampo


class PersonalNombresFechasHistorialTest(unittest.TestCase):
    setUp = fixtures.PersonalAltaPTAATest.setUp
    tearDown = fixtures.PersonalAltaPTAATest.tearDown
    payload = fixtures.PersonalAltaPTAATest.payload

    def structured(self, **changes):
        data = self.payload(**{"nombre": "María del Carmen", "apellido": "De la Cruz", **changes})
        data.pop("nombre_apellido")
        return data

    def test_nombre_compuesto_persistencia_edicion_y_snapshot(self):
        persona = crear_personal(self.structured(), 1)
        db.session.expire_all()
        self.assertEqual(persona.serialize()["nombre"], "María del Carmen")
        self.assertEqual(persona.serialize()["apellido"], "De la Cruz")
        self.assertEqual(persona.nombre_apellido, "María del Carmen De la Cruz")
        self.assertEqual(nombre_para_memoria(persona), "María del Carmen, DE LA CRUZ")
        actualizar_personal(persona.id, {"apellido": "Del Río"}, "personal", 1)
        self.assertEqual(persona.nombre_apellido, "María del Carmen Del Río")
        history = obtener_historial_personal_por_rol(persona.id, "personal")
        self.assertTrue(any(item["campo"] == "apellido" for item in history))
        before = len(history)
        actualizar_personal(persona.id, {"apellido": "Del Río"}, "personal", 1)
        self.assertEqual(len(obtener_historial_personal_por_rol(persona.id, "personal")), before)

    def test_campos_vacios_o_invalidos_rechazados(self):
        for campo in ("nombre", "apellido"):
            for valor in (None, "", "  ", "Nombre 123", "a" * 61):
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValidationError):
                    crear_personal(self.structured(**{campo: valor}), 1)
                db.session.rollback()

    def test_historico_se_conserva_y_se_puede_estructurar(self):
        persona = crear_personal(self.payload(), 1)
        persona.nombre = persona.apellido = None
        db.session.commit()
        self.assertIsNone(persona.nombre)
        self.assertEqual(nombre_para_memoria(persona), "Persona PTAA")
        actualizar_personal(persona.id, {"horas_semanales": 21}, "personal", 1)
        actualizar_personal(persona.id, {"nombre": "Persona", "apellido": "PTAA"}, "personal", 1)
        self.assertEqual((persona.nombre, persona.apellido), ("Persona", "PTAA"))
        with self.assertRaises(ValidationError):
            actualizar_personal(persona.id, {"nombre_apellido": "Otra Persona"}, "personal", 1)

    def test_alta_exige_nombres_separados_en_las_tres_clases(self):
        data = self.payload()
        data.pop("nombre")
        data.pop("apellido")
        for create, extra in ((crear_personal, {}), (crear_becario, {"tipo_formacion_id": 1}),
                              (crear_investigador, {"tipo_dedicacion_id": 1})):
            with self.subTest(create=create.__name__), self.assertRaises(ValidationError):
                create({**data, **extra}, 1)
            db.session.rollback()
        response = self.client.post("/api/v1/personal", json=data, headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 400)

    def test_fechas_limites_y_futuras(self):
        for value in ("2010-01-01", date.today().isoformat()):
            self.assertEqual(validar_fecha_alta_grupo(value).isoformat(), value)
        for value in ("2009-12-31", "9999-12-31", (date.today() + timedelta(days=1)).isoformat()):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validar_fecha_alta_grupo(value)
        persona = crear_personal(self.structured(), 1)
        response = self.client.put(f"/api/v1/personal/personal/{persona.id}",
            json={"fecha_alta_grupo": "9999-12-31"}, headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("fecha_alta_grupo", response.get_json()["error"]["details"]["fields"])

    def test_tres_clases_guardan_nombres_y_rechazan_futuro(self):
        for create, extra, update in (
            (crear_becario, {"tipo_formacion_id": 1}, actualizar_becario),
            (crear_investigador, {"tipo_dedicacion_id": 1}, actualizar_investigador),
        ):
            with self.subTest(create=create.__name__):
                with self.assertRaises(ValidationError):
                    create(self.structured(fecha_alta_grupo="9999-12-31", **extra), 1)
                db.session.rollback()
                persona = create(self.structured(**extra), 1)
                self.assertEqual(persona.apellido, "De la Cruz")
                update(persona.id, {"nombre": "Ana María"}, 1)
                self.assertEqual(persona.nombre_apellido, "Ana María De la Cruz")
                with self.assertRaises(ValidationError):
                    update(persona.id, {"fecha_alta_grupo": "9999-12-31"}, 1)
                db.session.rollback()
                db.session.delete(persona.identidad)
                db.session.delete(persona)
                db.session.commit()

    def test_historial_etiquetas_inactivos_no_disponibles_y_paginacion(self):
        from modules.personal.models.tipo_personal import TipoPersonal
        persona = crear_personal(self.structured(), 1)
        anterior = db.session.get(TipoPersonal, 1).nombre
        actualizar_personal(persona.id, {"tipo_personal_id": 2}, "personal", 1)
        db.session.get(TipoPersonal, 1).activo = False
        db.session.commit()
        history = obtener_historial_personal_por_rol(persona.id, "personal")
        row = next(item for item in history if item["campo"] == "tipo_personal_id")
        self.assertEqual(row["valor_anterior"], 1)
        self.assertEqual(row["valor_anterior_nombre"], anterior)
        self.assertEqual(row["valor_nuevo_nombre"], "Profesional")
        db.session.add(AuditoriaCampo(entidad="personal", registro_id=persona.id,
            campo="tipo_personal_id", valor_anterior=9999, valor_nuevo=None, usuario_id=1))
        db.session.commit()
        response = self.client.get(f"/api/v1/personal/personal/{persona.id}/historial?page=1&per_page=3",
            headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["meta"]["per_page"], 3)
        self.assertEqual(body["data"][0]["valor_anterior_nombre"], "Referencia no disponible")
        self.assertEqual(body["data"][0]["valor_nuevo_nombre"], "Sin dato")

    def test_historial_resuelve_catalogos_de_investigador(self):
        from modules.catalogos.models.categoria_utn import CategoriaUtn
        from modules.grupo.models.programa_incentivos import ProgramaIncentivos
        db.session.add_all([CategoriaUtn(id=1, nombre="Categoría anterior"), CategoriaUtn(id=2, nombre="Categoría nueva"),
                            ProgramaIncentivos(id=1, nombre="Programa anterior"), ProgramaIncentivos(id=2, nombre="Programa nuevo")])
        db.session.commit()
        persona = crear_investigador(self.structured(tipo_dedicacion_id=1, categoria_utn_id=1, programa_incentivos_id=1), 1)
        actualizar_personal(persona.id, {"categoria_utn_id": 2, "programa_incentivos_id": 2}, "investigador", 1)
        history = obtener_historial_personal_por_rol(persona.id, "investigador")
        labels = {item["campo"]: (item["valor_anterior_nombre"], item["valor_nuevo_nombre"]) for item in history}
        self.assertEqual(labels["categoria_utn_id"], ("Categoría anterior", "Categoría nueva"))
        self.assertEqual(labels["programa_incentivos_id"], ("Programa anterior", "Programa nuevo"))
        db.session.add(AuditoriaCampo(entidad="investigador", registro_id=persona.id,
            campo="tipo_dedicacion_id", valor_anterior=None, valor_nuevo=1, usuario_id=1))
        db.session.commit()
        row = obtener_historial_personal_por_rol(persona.id, "investigador")[0]
        self.assertEqual(row["valor_nuevo_nombre"], "Simple")

    def test_excel_del_grupo_compone_los_tres_nombres(self):
        from openpyxl import load_workbook
        from modules.memorias.services.exportacion_service_impl import ExportService
        crear_personal(self.structured(), 1)
        crear_becario(self.structured(tipo_formacion_id=1, dni="12345679", cuil="20-12345679-4"), 1)
        crear_investigador(self.structured(tipo_dedicacion_id=1, dni="12345670", cuil="20-12345670-0"), 1)
        workbook = load_workbook(ExportService.generar_excel_grupo(1))
        values = [cell.value for sheet in workbook for row in sheet for cell in row]
        self.assertEqual(values.count("María del Carmen, DE LA CRUZ"), 3)
