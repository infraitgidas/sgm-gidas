import unittest
from datetime import date
from unittest.mock import patch

from flask import Flask
from extension import db
from sqlalchemy.dialects import postgresql
from modules import models_registry  # noqa: F401
from modules.personal.models.personal import Investigador, Becario
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion, InvestigadorProyecto, TipoProyecto
from modules.proyectos.routes.proyecto_investigacion_rutas import proyecto_investigacion_bp
from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.personal.services.investigador_service import listar_investigadores


class ProyectoCoordinadorTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(proyecto_investigacion_bp, url_prefix="/api/v1/proyectos")
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all([
            TipoProyecto(id=1, nombre="Investigación", activo=True),
            Investigador(id=1, nombre_apellido="Coordinador A", horas_semanales=20, activo=True),
            Investigador(id=2, nombre_apellido="Coordinador B", horas_semanales=20, activo=True),
            Investigador(id=3, nombre_apellido="Inactivo", horas_semanales=20, activo=False),
            Investigador(id=4, nombre_apellido="Baja", horas_semanales=20, activo=True, deleted_at=date(2026, 1, 1)),
            Becario(id=5, nombre_apellido="Becario", horas_semanales=20, activo=True, tipo_formacion_id=1),
        ])
        db.session.commit()
        self.client = self.app.test_client()
        self.auth = patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": "GESTOR"})
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.headers = {"Authorization": "Bearer test"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def create(self, **changes):
        return self.client.post("/api/v1/proyectos", headers=self.headers, json={
            "codigo_proyecto": "ABC1", "nombre_proyecto": "Proyecto",
            "descripcion_proyecto": "Descripción", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31",
            "tipo_proyecto_id": 1, "investigadores_ids": [1, 2], "coordinador_id": 1,
            **changes,
        })

    def update(self, id, data):
        return self.client.put(f"/api/v1/proyectos/{id}", headers=self.headers, json=data)

    def test_bloqueo_de_edicion_solo_afecta_la_tabla_proyecto(self):
        query = ProyectoInvestigacionService._query_proyecto_activo_bloqueado(1)
        sql = str(query.statement.compile(dialect=postgresql.dialect()))

        self.assertIn("FOR UPDATE OF proyecto_investigacion", sql)

    def test_asignacion_y_consulta_posterior(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.get_json())
        id = response.get_json()["id"]
        detail = self.client.get(f"/api/v1/proyectos/{id}", headers=self.headers).get_json()
        self.assertEqual(next(i["id"] for i in detail["investigadores"] if i["es_coordinador"]), 1)
        self.assertEqual(AuditoriaCampo.query.count(), 0)

        response = self.update(id, {"becarios_ids": [5]})
        self.assertEqual(response.status_code, 200, response.get_json())
        evento = AuditoriaCampo.query.filter_by(campo="becarios_ids").one()
        self.assertEqual(evento.valor_nuevo, {
            "accion": "vincular",
            "detalle": {"id": 5, "nombre_apellido": "Becario"},
        })

    def test_listado_paginado_busca_ordena_y_conserva_contrato_plano(self):
        for index in range(1, 11):
            response = self.create(
                codigo_proyecto=f"COD{index}",
                nombre_proyecto=f"Proyecto {index:02d}",
            )
            self.assertEqual(response.status_code, 201, response.get_json())

        page = self.client.get(
            "/api/v1/proyectos?page=2&per_page=9&sort=nombre&direction=asc",
            headers=self.headers,
        )
        self.assertEqual(page.status_code, 200, page.get_json())
        self.assertEqual(page.get_json()["meta"]["total"], 10)
        self.assertEqual(page.get_json()["meta"]["total_pages"], 2)
        self.assertEqual(len(page.get_json()["data"]), 1)

        search = self.client.get(
            "/api/v1/proyectos?page=1&per_page=9&search=Proyecto%2007",
            headers=self.headers,
        )
        self.assertEqual(search.status_code, 200, search.get_json())
        self.assertEqual(search.get_json()["meta"]["total"], 1)
        self.assertEqual(search.get_json()["data"][0]["codigo_proyecto"], "COD7")

        legacy = self.client.get("/api/v1/proyectos", headers=self.headers)
        self.assertEqual(legacy.status_code, 200, legacy.get_json())
        self.assertIsInstance(legacy.get_json(), list)

    def test_listado_paginado_distingue_activos_y_cerrados(self):
        active = self.create(codigo_proyecto="ABIERTO", nombre_proyecto="Proyecto activo")
        closed = self.create(
            codigo_proyecto="CERRADO",
            nombre_proyecto="Proyecto cerrado",
            fecha_inicio="2024-01-01", fecha_fin="2024-12-31",
        )
        self.assertEqual(active.status_code, 201, active.get_json())
        self.assertEqual(closed.status_code, 201, closed.get_json())

        active_page = self.client.get(
            "/api/v1/proyectos?page=1&per_page=9&activos=true",
            headers=self.headers,
        ).get_json()
        closed_page = self.client.get(
            "/api/v1/proyectos?page=1&per_page=9&activos=false",
            headers=self.headers,
        ).get_json()
        self.assertEqual([item["codigo_proyecto"] for item in active_page["data"]], ["ABIERTO", "CERRADO"])
        self.assertEqual([item["codigo_proyecto"] for item in closed_page["data"]], [])

    def test_listado_paginado_rechaza_limite_superior_a_nueve(self):
        response = self.client.get(
            "/api/v1/proyectos?page=1&per_page=10",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(response.get_json()["error"]["code"], "VALIDATION_ERROR")

        invalid_filter = self.client.get(
            "/api/v1/proyectos?page=1&tipo_proyecto_id=no-valido",
            headers=self.headers,
        )
        self.assertEqual(invalid_filter.status_code, 400, invalid_filter.get_json())
        self.assertEqual(invalid_filter.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_candidatos_invalidos_no_dejan_proyecto_parcial(self):
        for id in (999, 3, 4, 5, 0, True):
            with self.subTest(id=id):
                response = self.create(investigadores_ids=[id], coordinador_id=id)
                self.assertEqual(response.status_code, 400, response.get_json())
                self.assertEqual(ProyectoInvestigacion.query.count(), 0)
                self.assertEqual(InvestigadorProyecto.query.count(), 0)
                self.assertEqual(AuditoriaCampo.query.count(), 0)

    def test_reemplazo_preserva_participaciones_y_fecha(self):
        id = self.create().get_json()["id"]
        rows = [(p.id, p.fecha_inicio) for p in InvestigadorProyecto.query.order_by(InvestigadorProyecto.id)]
        response = self.update(id, {"coordinador_id": 2})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(rows, [(p.id, p.fecha_inicio) for p in InvestigadorProyecto.query.order_by(InvestigadorProyecto.id)])
        self.assertEqual(InvestigadorProyecto.query.filter_by(es_coordinador=True, deleted_at=None).count(), 1)
        self.assertEqual(InvestigadorProyecto.query.filter_by(es_coordinador=True).first().id_investigador, 2)

    def test_edicion_sin_coordinador_conserva_asignacion(self):
        id = self.create().get_json()["id"]
        response = self.update(id, {"nombre_proyecto": "Otro nombre"})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(InvestigadorProyecto.query.filter_by(es_coordinador=True).first().id_investigador, 1)

    def test_baja_del_coordinador_conservacion_y_reemplazo(self):
        id = self.create().get_json()["id"]
        persona = db.session.get(Investigador, 1)
        persona.activo = False
        persona.soft_delete(7)
        db.session.commit()
        self.assertEqual(self.update(id, {"nombre_proyecto": "Conservado"}).status_code, 200)
        response = self.update(id, {"coordinador_id": 2, "investigadores_ids": [2]})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertIsNotNone(InvestigadorProyecto.query.filter_by(id_investigador=1).first().deleted_at)

    def test_rollback_de_campos_relaciones_e_historial(self):
        id = self.create().get_json()["id"]
        previous = AuditoriaCampo.query.count()
        with patch("modules.proyectos.services.proyecto_guardado_service.AuditoriaService.registrar_evento_relacion", side_effect=RuntimeError("fallo")):
            response = self.update(id, {"nombre_proyecto": "No persistir", "investigadores_ids": [2], "coordinador_id": 2})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(db.session.get(ProyectoInvestigacion, id).nombre_proyecto, "Proyecto")
        self.assertEqual(InvestigadorProyecto.query.filter_by(deleted_at=None).count(), 2)
        self.assertEqual(AuditoriaCampo.query.count(), previous)

    def test_rechaza_duplicados_coordinador_externo_y_null(self):
        for changes in ({"investigadores_ids": [1, 1]}, {"coordinador_id": 3}, {"coordinador_id": None}):
            self.assertEqual(self.create(**changes).status_code, 400)
            self.assertEqual(ProyectoInvestigacion.query.count(), 0)

    def test_lectura_no_puede_asignar(self):
        with patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": "LECTURA"}):
            self.assertEqual(self.create().status_code, 403)

    def test_listado_ofrece_solo_investigadores_activos(self):
        self.assertEqual({i.id for i in listar_investigadores()}, {1, 2})
        self.assertEqual({i.id for i in listar_investigadores("false")}, {3, 4})

    def test_guardado_repetido_no_duplica_relaciones_ni_historial(self):
        id = self.create().get_json()["id"]
        count = AuditoriaCampo.query.count()
        response = self.update(id, {"investigadores_ids": [1, 2], "coordinador_id": 1})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(InvestigadorProyecto.query.count(), 2)
        self.assertEqual(AuditoriaCampo.query.count(), count)

    def test_fallo_commit_revierte_alta(self):
        with patch("modules.proyectos.services.proyecto_guardado_service.db.session.commit", side_effect=RuntimeError("fallo")):
            response = self.create()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(ProyectoInvestigacion.query.count(), 0)
        self.assertEqual(AuditoriaCampo.query.count(), 0)

    def test_alta_con_fecha_fin_pasada_presente_y_futura(self):
        for fecha_fin in ("2024-12-31", date.today().isoformat(), "2026-12-31"):
            with self.subTest(fecha_fin=fecha_fin):
                response = self.create(fecha_inicio="2024-01-01", fecha_fin=fecha_fin, becarios_ids=[5])
                self.assertEqual(response.status_code, 201, response.get_json())
                id = response.get_json()["id"]
                detail = self.client.get(f"/api/v1/proyectos/{id}", headers=self.headers).get_json()
                self.assertEqual(detail["fecha_fin"], fecha_fin)
                self.assertEqual(next(p["id"] for p in detail["investigadores"] if p["es_coordinador"]), 1)
                self.assertEqual(detail["becarios"][0]["id"], 5)
                expected = fecha_fin if fecha_fin <= date.today().isoformat() else None
                self.assertEqual(detail["investigadores"][0]["fecha_fin"], expected)

    def test_proyecto_con_fecha_vencida_sin_informe_admite_cambio(self):
        response = self.create(fecha_inicio="2024-01-01", fecha_fin="2024-12-31")
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(self.update(response.get_json()["id"], {"coordinador_id": 2}).status_code, 200)

    def test_fecha_fin_anterior_al_inicio_no_deja_alta_parcial(self):
        response = self.create(fecha_fin="2025-12-31")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProyectoInvestigacion.query.count(), 0)

    def test_prorroga_registra_motivo_y_rechaza_duplicado(self):
        created = self.create().get_json()
        url = f"/api/v1/proyectos/{created['id']}/prorroga"

        invalid = self.client.post(url, headers=self.headers, json={"motivo": " "})
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("motivo", invalid.get_json()["error"]["details"]["fields"])

        response = self.client.post(url, headers=self.headers, json={
            "motivo": "Se requiere completar los resultados pendientes."
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["fecha_fin_original"], "2026-12-31")
        self.assertEqual(response.get_json()["fecha_fin_prorrogada"], "2027-12-31")
        self.assertEqual(response.get_json()["fecha_fin"], "2027-12-31")
        self.assertEqual(AuditoriaCampo.query.filter_by(campo="prorroga").count(), 1)

        repeated = self.client.post(url, headers=self.headers, json={
            "motivo": "Se requiere completar los resultados pendientes."
        })
        self.assertEqual(repeated.status_code, 409)

        closed = self.client.post(
            f"/api/v1/proyectos/{created['id']}/cerrar",
            headers=self.headers,
            json={"fecha_fin": date.today().isoformat()},
        )
        self.assertEqual(closed.status_code, 409, closed.get_json())
        self.assertIn("informe PID", closed.get_json()["error"]["message"])
        detail = self.client.get(f"/api/v1/proyectos/{created['id']}", headers=self.headers).get_json()
        self.assertEqual(detail["fecha_fin_original"], "2026-12-31")
        self.assertEqual(detail["fecha_fin_prorrogada"], "2027-12-31")

    def test_editar_solo_fecha_fin_no_cierra_proyecto(self):
        created = self.create().get_json()
        changed = self.update(created["id"], {"fecha_fin": "2027-06-30"})
        self.assertEqual(changed.status_code, 200, changed.get_json())
        self.assertEqual(changed.get_json()["fecha_fin"], "2027-06-30")
        self.assertIsNone(changed.get_json()["deleted_at"])

        invalid = self.update(created["id"], {"fecha_fin": "2029-01-01"})
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("fecha_fin", invalid.get_json()["error"]["details"]["fields"])

    def test_prorroga_admite_proyecto_vencido_sin_baja_manual(self):
        created = self.create(fecha_inicio="2024-01-01", fecha_fin="2024-12-31").get_json()
        response = self.client.post(
            f"/api/v1/proyectos/{created['id']}/prorroga",
            headers=self.headers,
            json={"motivo": "Los resultados finales requieren más tiempo."},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["fecha_fin_prorrogada"], "2025-12-31")

    def test_prorroga_rechaza_rol_de_lectura(self):
        created = self.create().get_json()
        with patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": "LECTURA"}):
            response = self.client.post(
                f"/api/v1/proyectos/{created['id']}/prorroga",
                headers=self.headers,
                json={"motivo": "Resultados pendientes de revisión."},
            )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
