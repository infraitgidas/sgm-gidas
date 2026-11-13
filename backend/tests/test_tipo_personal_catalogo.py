import unittest
from unittest.mock import patch

from extension import db
from tests import test_personal_alta_ptaa as fixtures
from modules.personal.models.tipo_personal import TipoPersonal
from modules.personal.models.personal import Personal, PersonalMemoriaVersion
from modules.personal.services.personal_service import crear_personal, _validar_tipo_personal
from modules.personal.services.tipo_personal_service import crear_tipo_personal, actualizar_tipo_personal, listar_tipos, normalizar_nombre_tipo
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.exceptions import ConflictError, ValidationError
from tools.depurar_tipos_personal import depurar, huella_referencias


CONSERVAR = ["Técnico", "Administrativo", "De Apoyo", "Profesional"]


class TipoPersonalCatalogoTest(unittest.TestCase):
    tearDown = fixtures.PersonalAltaPTAATest.tearDown
    payload = fixtures.PersonalAltaPTAATest.payload

    def setUp(self):
        fixtures.PersonalAltaPTAATest.setUp(self)
        db.session.get(TipoPersonal, 1).nombre = "Técnico"
        db.session.add_all([
            TipoPersonal(id=3, nombre="Administrativo"),
            TipoPersonal(id=4, nombre="De Apoyo"),
            TipoPersonal(id=9, nombre="TAA"),
            TipoPersonal(id=10, nombre="Técnico, administrativo y de apoyo"),
            TipoPersonal(id=11, nombre="  tecnico  "),
        ])
        db.session.commit()
        persona = crear_personal(self.payload(tipo_personal_id=9), 1)
        self.persona_id = persona.id
        db.session.add(PersonalMemoriaVersion(personal_id=persona.id, memoria_version_id=1,
            nombre_apellido="Nombre histórico", tipo_personal_id=9, tipo_personal_nombre="TAA", grupo_utn_id=1))
        db.session.commit()

    def test_vista_previa_y_aplicacion_conservan_personas_fotos_y_referencias(self):
        antes = huella_referencias()
        plan = depurar(CONSERVAR)
        self.assertEqual([item["id"] for item in plan], [9, 10, 11])
        self.assertEqual(len(listar_tipos()), 7)
        self.assertEqual(AuditoriaCampo.query.count(), 0)
        depurar(CONSERVAR, aplicar=True, esperados=[9, 10, 11])
        self.assertEqual(huella_referencias(), antes)
        self.assertEqual({tipo.nombre for tipo in listar_tipos()}, set(CONSERVAR))
        self.assertEqual(TipoPersonal.query.count(), 7)
        self.assertEqual(db.session.get(Personal, self.persona_id).tipo_personal_id, 9)
        self.assertEqual(PersonalMemoriaVersion.query.one().tipo_personal_nombre, "TAA")
        self.assertEqual(AuditoriaCampo.query.filter_by(entidad="tipo_personal", campo="activo").count(), 3)
        self.assertEqual(AuditoriaCampo.query.filter_by(entidad="tipo_personal", campo="accion_sistema").count(), 6)
        for tipo_id in (9, 10, 11):
            with self.assertRaises(ValidationError):
                _validar_tipo_personal(tipo_id)

    def test_requiere_confirmar_el_plan_y_no_admite_nombres_ausentes(self):
        for esperados in (None, [9, 10]):
            with self.assertRaises(ValueError):
                depurar(CONSERVAR, aplicar=True, esperados=esperados)
        with self.assertRaises(ValueError):
            depurar([*CONSERVAR, "No existe"])
        self.assertEqual(len(listar_tipos()), 7)
        self.assertEqual(AuditoriaCampo.query.count(), 0)

    def test_repetir_la_depuracion_es_idempotente(self):
        depurar(CONSERVAR, aplicar=True, esperados=[9, 10, 11])
        eventos = AuditoriaCampo.query.count()
        self.assertEqual(depurar(CONSERVAR, aplicar=True, esperados=[]), [])
        self.assertEqual(AuditoriaCampo.query.count(), eventos)

    def test_un_fallo_de_auditoria_revierte_todo(self):
        antes = huella_referencias()
        with patch("tools.depurar_tipos_personal.CatalogoAuditoriaService.registrar_accion", side_effect=RuntimeError("Fallo de escritura")):
            with self.assertRaises(RuntimeError):
                depurar(CONSERVAR, aplicar=True, esperados=[9, 10, 11])
        self.assertEqual(len(listar_tipos()), 7)
        self.assertEqual(AuditoriaCampo.query.count(), 0)
        self.assertEqual(huella_referencias(), antes)

    def test_duplicados_normalizados_no_se_crean_ni_se_asignan_a_otro_tipo(self):
        nuevo = crear_tipo_personal({"nombre": "Especialista de laboratorio"})
        self.assertEqual(normalizar_nombre_tipo("TÉCNICO, Administrativo"), normalizar_nombre_tipo("tecnico administrativo"))
        for nombre in ("  Especialista   de laboratorio ", "ESPECIALISTA DE LABORATORIO", "Especialísta-de-laboratorio"):
            with self.subTest(nombre=nombre), self.assertRaises(ConflictError):
                crear_tipo_personal({"nombre": nombre})
            with self.assertRaises(ConflictError):
                actualizar_tipo_personal(3, {"nombre": nombre})
        actualizado = actualizar_tipo_personal(nuevo.id, {"nombre": "ESPECIALISTA de laboratorio"})
        self.assertEqual(actualizado.nombre, "ESPECIALISTA de laboratorio")
        depurar(CONSERVAR, aplicar=True, esperados=[9, 10, 11, nuevo.id])
        with self.assertRaises(ConflictError):
            crear_tipo_personal({"nombre": "especialista de laboratorio"})


if __name__ == "__main__":
    unittest.main()
