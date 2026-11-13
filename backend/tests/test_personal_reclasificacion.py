import unittest
from datetime import date
from unittest.mock import patch

from flask import g
from extension import db
from tests import test_personal_alta_ptaa as fixtures
from modules.personal.models.personal import Personal, Becario, Investigador, PersonalMemoriaVersion
from modules.personal.models.identidad import IdentidadPersonal
from modules.personal.services.personal_service import crear_personal, actualizar_personal, eliminar_personal_por_rol
from modules.personal.services.reclasificacion_service import reclasificar_personal, CLASES
from modules.shared.exceptions import ConflictError, ValidationError, NotFoundError, ForbiddenError
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.services.tenant_scope import register_tenant_orm_policy
from modules.shared.services.form_draft_service import FormDraftService


class PersonalReclasificacionTest(unittest.TestCase):
    setUp = fixtures.PersonalAltaPTAATest.setUp
    tearDown = fixtures.PersonalAltaPTAATest.tearDown
    payload = fixtures.PersonalAltaPTAATest.payload

    def persona(self):
        return crear_personal(self.payload(), 1)

    def cambios(self, destino):
        return {"clase_destino": destino, **{
            "personal": {"tipo_personal_id": 1},
            "becario": {"tipo_formacion_id": 1},
            "investigador": {"tipo_dedicacion_id": 1},
        }[destino]}

    def test_seis_transiciones_conservan_identidad_horas_auditoria_y_un_solo_registro(self):
        persona = self.persona()
        identidad, creado = persona.identidad_id, persona.created_at
        actualizar_personal(persona.id, {"horas_semanales": 21}, "personal", 1)
        actual = {"rol": "personal", "id": persona.id}
        for destino in ("becario", "investigador", "personal", "investigador", "becario", "personal"):
            with self.subTest(origen=actual["rol"], destino=destino):
                actual = reclasificar_personal(actual["rol"], actual["id"], self.cambios(destino), 1)
                self.assertEqual(actual["rol"], destino)
                self.assertEqual(actual["identidad_id"], identidad)
                self.assertEqual(actual["dni"], "12345678")
                self.assertEqual(actual["cuil"], "20-12345678-6")
                self.assertEqual(actual["nombre"], "Persona")
                self.assertEqual(actual["horas_semanales"], 21)
                self.assertEqual(len(actual["historial_horas"]), 2)
                self.assertEqual(sum(h["fecha_fin"] is None for h in actual["historial_horas"]), 1)
                self.assertEqual(sum(m.query.count() for m in (Personal, Becario, Investigador)), 1)
                self.assertEqual(IdentidadPersonal.query.count(), 1)
                self.assertEqual(db.session.get(CLASES[destino][0], actual["id"]).created_at, creado)
        self.assertEqual(AuditoriaCampo.query.filter_by(entidad="personal", registro_id=actual["id"], campo="clase_registro").count(), 6)
        self.assertEqual(AuditoriaCampo.query.filter_by(campo="horas_semanales").count(), 1)

    def test_id_destino_ocupado_no_sobrescribe_otra_persona(self):
        persona = self.persona()
        otro = Becario(id=persona.id, nombre_apellido="Otra Persona", horas_semanales=5, tipo_formacion_id=1)
        db.session.add(otro)
        db.session.commit()
        resultado = reclasificar_personal("personal", persona.id, self.cambios("becario"), 1)
        self.assertNotEqual(resultado["id"], otro.id)
        self.assertEqual(db.session.get(Becario, otro.id).nombre_apellido, "Otra Persona")

    def test_permite_editar_datos_comunes_en_la_misma_transaccion(self):
        persona = self.persona()
        data = reclasificar_personal("personal", persona.id, {**self.cambios("becario"), "nombre": "Nuevo Nombre", "horas_semanales": 30}, 1)
        self.assertEqual(data["nombre_apellido"], "Nuevo Nombre PTAA")
        self.assertEqual(data["horas_semanales"], 30)
        self.assertEqual(len(data["historial_horas"]), 2)
        self.assertEqual(sum(h["fecha_fin"] is None for h in data["historial_horas"]), 1)

    def test_bloquea_vinculos_tambien_despues_de_su_baja_logica(self):
        from modules.recursos.models.becas import Beca, Beca_Becario
        from datetime import datetime
        persona = self.persona()
        resultado = reclasificar_personal("personal", persona.id, self.cambios("becario"), 1)
        beca = Beca(nombre_beca="Beca prueba", created_by=1)
        db.session.add(beca)
        db.session.flush()
        vinculo = Beca_Becario(id_beca=beca.id, id_becario=resultado["id"], fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 1), created_by=1)
        db.session.add(vinculo)
        db.session.commit()
        for eliminado in (None, datetime.utcnow()):
            vinculo.deleted_at = eliminado
            db.session.commit()
            with self.assertRaisesRegex(ConflictError, "vínculos"):
                reclasificar_personal("becario", resultado["id"], self.cambios("investigador"), 1)
            self.assertEqual(Beca_Becario.query.count(), 1)
            self.assertEqual(Investigador.query.count(), 0)

    def test_campos_destino_invalidos_no_dejan_cambios_parciales(self):
        persona = self.persona()
        for cambios in ({"tipo_formacion_id": 999}, {"tipo_formacion_id": True}, {"horas_semanales": 200}, {"apellido": "123"}, {"activo": False}, {"tipo_personal_id": 1}):
            with self.subTest(cambios=cambios), self.assertRaises(ValidationError):
                reclasificar_personal("personal", persona.id, {**self.cambios("becario"), **cambios}, 1)
            self.assertEqual(Personal.query.count(), 1)
            self.assertEqual(Becario.query.count(), 0)
            self.assertEqual(AuditoriaCampo.query.count(), 0)

    def test_rollback_incluso_despues_de_crear_destino_y_borrar_origen(self):
        persona = self.persona()
        actualizar_personal(persona.id, {"horas_semanales": 22}, "personal", 1)
        with patch("modules.personal.services.reclasificacion_service._sincronizar_becas", side_effect=ValidationError("Beca inválida")):
            with self.assertRaises(ValidationError):
                reclasificar_personal("personal", persona.id, {**self.cambios("becario"), "becas": [1]}, 1)
        self.assertEqual(Personal.query.count(), 1)
        self.assertEqual(Becario.query.count(), 0)
        self.assertEqual(len(db.session.get(Personal, persona.id).historial_horas), 2)
        self.assertEqual(AuditoriaCampo.query.filter_by(entidad="personal").count(), 1)

    def test_no_cambia_registros_inactivos_o_clases_invalidas(self):
        persona = self.persona()
        for data in (None, [], {"clase_destino": []}, {"clase_destino": "personal"}, {"clase_destino": "profesional"}):
            with self.assertRaises(ValidationError):
                reclasificar_personal("personal", persona.id, data, 1)
        eliminar_personal_por_rol(persona.id, "personal", 1)
        with self.assertRaises(ConflictError):
            reclasificar_personal("personal", persona.id, self.cambios("becario"), 1)

    def test_fotos_heredadas_sin_identidad_permiten_cambio_y_conservan_contenido(self):
        persona = self.persona()
        foto = PersonalMemoriaVersion(personal_id=persona.id, memoria_version_id=1, nombre_apellido="Nombre histórico", tipo_personal_id=1, grupo_utn_id=1)
        db.session.add(foto)
        db.session.commit()
        identidad = persona.identidad_id
        anterior = foto.serialize()
        reclasificar_personal("personal", persona.id, self.cambios("becario"), 1)
        db.session.expire_all()
        self.assertEqual(PersonalMemoriaVersion.query.one().serialize(), {**anterior, "identidad_id": identidad})
        self.assertEqual(Becario.query.count(), 1)
        self.assertEqual(Personal.query.count(), 0)

    def test_versiones_sucesivas_y_excel_conservan_fotos_de_cada_clase(self):
        from datetime import datetime
        from openpyxl import load_workbook
        from modules.memorias.models.memorias import Memoria, MemoriaVersion, EstadoMemoria
        from modules.memorias.services.exportacion_service_impl import ExportService
        from modules.personal.services.personal_service import snapshot_personal_para_memoria_version
        from modules.personal.services.becario_service import snapshot_becarios_para_memoria_version
        from modules.personal.services.investigador_service import snapshot_investigadores_para_memoria_version
        from modules.personal.services.reclasificacion_service import SNAPSHOTS
        persona = self.persona()
        identidad = persona.identidad_id
        memoria = Memoria(grupo_utn_id=1, periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31))
        db.session.add(memoria)
        db.session.commit()
        actual = {"rol": "personal", "id": persona.id}
        fotos, contenidos_excel = [], []
        for numero, destino in enumerate(("becario", "investigador", "personal", "investigador", "becario", "personal"), 1):
            version = MemoriaVersion(memoria_id=memoria.id, numero_version=numero, estado=EstadoMemoria.CERRADA,
                                     fecha_apertura=datetime(2026, 1, 1), contexto_institucional={"grupo": {
                                         "id": 1, "nombre_sigla_grupo": "Grupo", "nombre_unidad_academica": "UTN",
                                         "mail": "grupo@example.com", "objetivo_desarrollo": "Objetivo histórico",
                                     }})
            db.session.add(version)
            db.session.flush()
            generadas = [foto for generar in (snapshot_personal_para_memoria_version, snapshot_becarios_para_memoria_version, snapshot_investigadores_para_memoria_version) for foto in generar(version, 1)]
            db.session.commit()
            self.assertEqual(len(generadas), 1, "La versión incluye una sola clase para la persona")
            self.assertEqual(generadas[0].identidad_id, identidad)
            fotos.append((type(generadas[0]), generadas[0].id, generadas[0].serialize()))
            workbook = load_workbook(ExportService.generar_excel_memoria(memoria.id, version.id))
            contenidos_excel.append((version.id, {sheet.title: list(sheet.values) for sheet in workbook}))
            actual = reclasificar_personal(actual["rol"], actual["id"], self.cambios(destino), 1)
            for modelo, foto_id, esperado in fotos:
                self.assertEqual(db.session.get(modelo, foto_id).serialize(), esperado)
            for version_id, esperado in contenidos_excel:
                wb = load_workbook(ExportService.generar_excel_memoria(memoria.id, version_id))
                self.assertEqual({sheet.title: list(sheet.values) for sheet in wb}, esperado)
            for clase, modelo in SNAPSHOTS.items():
                self.assertEqual(modelo.query.filter_by(memoria_version_id=version.id).count(), int(clase == fotos[-1][0].__tablename__.removesuffix("_memoria_version")))

    def test_api_permiso_lectura_y_contrato_historial(self):
        persona = self.persona()
        ruta = f"/api/v1/personal/personal/{persona.id}/reclasificar"
        headers = {"Authorization": "Bearer test"}
        with patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "1", "rol": "LECTURA"}):
            self.assertEqual(self.client.put(ruta, json=self.cambios("becario"), headers=headers).status_code, 403)
        response = self.client.put(ruta, json=self.cambios("becario"), headers=headers)
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        historial = self.client.get(f"/api/v1/personal/becario/{data['id']}/historial?page=1&per_page=3", headers=headers)
        self.assertEqual(historial.status_code, 200)
        self.assertEqual(historial.get_json()["meta"]["per_page"], 3)
        self.assertTrue(any(item["campo"] == "clase_registro" for item in historial.get_json()["data"]))

    def test_foto_sigue_visible_para_su_uct_y_oculta_para_otra_despues_de_reclasificar(self):
        from datetime import datetime
        from modules.memorias.models.memorias import Memoria, MemoriaVersion, EstadoMemoria
        from modules.personal.services.personal_service import snapshot_personal_para_memoria_version, obtener_snapshots_personal_por_memoria_version
        persona = self.persona()
        memoria = Memoria(grupo_utn_id=1, periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31))
        version = MemoriaVersion(memoria=memoria, numero_version=1, estado=EstadoMemoria.CERRADA, fecha_apertura=datetime(2026, 1, 1))
        db.session.add(version)
        db.session.flush()
        snapshot_personal_para_memoria_version(version, 1)
        db.session.commit()
        version_id = version.id
        register_tenant_orm_policy()
        with self.app.test_request_context("/reclasificar"):
            g.current_grupo_utn_id = 1
            reclasificar_personal("personal", persona.id, self.cambios("becario"), 1)
            self.assertEqual(len(obtener_snapshots_personal_por_memoria_version(version_id)), 1)
        db.session.remove()
        with self.app.test_request_context("/snapshots"):
            g.current_grupo_utn_id = 2
            self.assertEqual(obtener_snapshots_personal_por_memoria_version(version_id), [])

    def test_otra_uct_no_puede_reclasificar(self):
        persona = self.persona()
        register_tenant_orm_policy()
        db.session.remove()
        with self.app.test_request_context("/reclasificar"):
            g.current_grupo_utn_id = 2
            with self.assertRaises(NotFoundError):
                reclasificar_personal("personal", 1, self.cambios("becario"), 1)

    def test_no_admite_fotos_con_origen_o_identidad_de_otra_uct(self):
        from datetime import datetime
        from modules.memorias.models.memorias import Memoria, MemoriaVersion
        otro = Personal(nombre_apellido="Persona ajena", horas_semanales=20, grupo_utn_id=2, tipo_personal_id=1,
                        identidad=IdentidadPersonal(dni="76543210", cuil="20-76543210-3"))
        version = MemoriaVersion(memoria=Memoria(grupo_utn_id=1, periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31)),
                                numero_version=1, fecha_apertura=datetime(2026, 1, 1))
        db.session.add_all([otro, version])
        db.session.commit()
        origen_id, identidad_id, version_id = otro.id, otro.identidad_id, version.id
        register_tenant_orm_policy()
        for identidad in (None, identidad_id):
            with self.app.test_request_context("/foto"):
                g.current_grupo_utn_id = 1
                db.session.add(PersonalMemoriaVersion(personal_id=origen_id, identidad_id=identidad, memoria_version_id=version_id,
                                                     nombre_apellido="Dato ajeno", tipo_personal_id=1, grupo_utn_id=1))
                with self.assertRaises(ForbiddenError):
                    db.session.flush()
                db.session.rollback()

    def test_borrador_reclasificacion_no_colisiona_con_edicion_y_recupera_destino(self):
        # La fixture no activa FKs SQLite; solo se verifica la clave y el enlace.
        a = FormDraftService.save(1, "personal-reclasificar-personal-becario", "1", {"nombreApellido": "Persona"})
        b = FormDraftService.save(1, "personal-becario", "1", {"nombreApellido": "Otra"})
        self.assertNotEqual(a["module"], b["module"])
        self.assertIn("/personal/personal/1/editar?tipo=BECARIO&reclasificar=true", a["path"])


if __name__ == "__main__":
    unittest.main()
