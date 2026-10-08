import unittest
from datetime import date, datetime
from io import BytesIO
from unittest.mock import patch

from flask import Flask
from openpyxl import load_workbook
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from extension import db
from modules import models_registry  # noqa: F401
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.personal.models.personal import Investigador, Becario, Personal, TipoFormacion
from modules.personal.models.tipo_personal import TipoPersonal
from modules.produccion.models.trabajo_autor import TrabajoReunionAutor, TrabajoRevistaAutor
from modules.produccion.models.trabajo_reunion import TipoReunion, TrabajoReunionCientifica
from modules.produccion.models.trabajo_revista import TipoRevista, TrabajosRevistasReferato
from modules.produccion.routes.trabajo_reunion_rutas import trabajo_reunion_cientifica_bp
from modules.produccion.routes.trabajo_revista_rutas import trabajos_revistas_referato_bp
from modules.produccion.services.trabajo_reunion_service import TrabajoReunionCientificaService
from modules.produccion.services.trabajo_revista_service import TrabajosRevistasReferatoService
from modules.memorias.models.memorias import Memoria, MemoriaVersion, EstadoMemoria
from modules.memorias.services.exportacion_service_impl import ExportService
from modules.memorias.services.memoria_contexto_service import snapshot_contexto_institucional
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.auth.models.usuario import Usuario, RolUsuario
from modules.search.services.search_service import SearchService


class TrabajoAutoresTest(unittest.TestCase):
    def test_referencias_invalidas_identifican_autores(self):
        from modules.produccion.services.trabajo_autores_service import validar_referencias
        from modules.shared.exceptions import ValidationError
        for autores in (["invalido"], [{"rol": "investigador", "id": 1}, {"rol": "investigador", "id": 1}]):
            with self.subTest(autores=autores), self.assertRaises(ValidationError) as caught:
                validar_referencias(autores)
            self.assertIn("autores", caught.exception.details["fields"])

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(trabajo_reunion_cientifica_bp, url_prefix="/reuniones")
        self.app.register_blueprint(trabajos_revistas_referato_bp, url_prefix="/revistas")
        self.context = self.app.app_context()
        self.context.push()
        # Enforce foreign keys too, rather than relying on SQLite defaults.
        event.listen(db.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        db.create_all()
        db.session.add_all([
            RolUsuario(id=1, nombre="GESTOR"),
            GrupoInvestigacionUtn(id=1, nombre_sigla_grupo="GIDAS", nombre_unidad_academica="UTN", mail="gidas@test.local", objetivo_desarrollo="Investigación"),
            TipoPersonal(id=1, nombre="Profesional"),
            TipoFormacion(id=1, nombre="Grado"),
            TipoReunion(id=1, nombre="Nacional"),
            TipoRevista(id=1, nombre="Nacional"),
        ])
        db.session.flush()
        db.session.add_all([
            Usuario(id=7, nombre_usuario="gestor", mail="gestor@test.local", contrasena="test", id_rol=1),
            Investigador(id=1, nombre_apellido="Ana Investigadora", horas_semanales=20, activo=True, grupo_utn_id=1),
            Becario(id=1, nombre_apellido="Luis Becario", horas_semanales=20, activo=True, tipo_formacion_id=1, grupo_utn_id=1),
            Personal(id=1, nombre_apellido="Eva Profesional", horas_semanales=20, activo=True, tipo_personal_id=1, grupo_utn_id=1),
            Investigador(id=2, nombre_apellido="Inactivo", horas_semanales=20, activo=False),
            Investigador(id=3, nombre_apellido="Eliminado", horas_semanales=20, activo=True, deleted_at=date(2026, 1, 1)),
        ])
        db.session.commit()
        self.client = self.app.test_client()
        self.auth = patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": "GESTOR"})
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.headers = {"Authorization": "Bearer test"}
        self.autores = [{"id": 1, "rol": rol} for rol in ("investigador", "becario")]

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def payload(self, tipo):
        comun = {"titulo_trabajo": "Estudio de sistemas", "grupo_utn_id": 1, "autores": self.autores}
        if tipo == "reuniones":
            return {**comun, "tipo_reunion_id": 1, "nombre_reunion": "Congreso UTN", "procedencia": "Argentina", "fecha_presentacion": "2026-03-20"}
        return {**comun, "tipo_revista_id": 1, "nombre_revista": "Revista UTN", "editorial": "UTN", "issn": "1234-5678", "pais": "Argentina", "fecha_publicacion": "2026-03-20"}

    def crear(self, tipo):
        respuesta = self.client.post(f"/{tipo}", json=self.payload(tipo), headers=self.headers)
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["id"]

    def test_alta_edicion_historial_filtros_y_consulta_ambos_trabajos(self):
        for tipo, entidad in (("reuniones", "trabajo_reunion_cientifica"), ("revistas", "trabajo_revista_referato")):
            with self.subTest(tipo=tipo):
                identificador = self.crear(tipo)
                detalle = self.client.get(f"/{tipo}/{identificador}", headers=self.headers).get_json()
                self.assertNotIn("investigadores", detalle)
                self.assertEqual({a["tipo"] for a in detalle["autores"]}, {"Investigador", "Becario"})
                self.assertEqual(len(self.client.get(f"/{tipo}?autor_rol=becario&autor_id=1", headers=self.headers).get_json()), 1)
                self.assertEqual(self.client.get(f"/{tipo}?autor_id=1", headers=self.headers).status_code, 400)
                self.assertEqual(self.client.get(f"/{tipo}?autor_rol=personal&autor_id=1", headers=self.headers).status_code, 400)
                eventos = AuditoriaCampo.query.filter_by(entidad=entidad, registro_id=identificador, campo="autores").all()
                self.assertEqual(len(eventos), 2)
                nuevo = self.client.put(f"/{tipo}/{identificador}", json={"autores": [self.autores[1]], "titulo_trabajo": "Estudio actualizado"}, headers=self.headers)
                self.assertEqual(nuevo.status_code, 200, nuevo.get_json())
                self.assertEqual([a["rol"] for a in nuevo.get_json()["autores"]], ["becario"])
                eventos = self.client.get(f"/{tipo}/{identificador}/historial", headers=self.headers).get_json()
                self.assertEqual(len(eventos), 4)
                # Repeating an unchanged update must not add historical events.
                self.client.put(f"/{tipo}/{identificador}", json={"autores": [self.autores[1]]}, headers=self.headers)
                self.assertEqual(AuditoriaCampo.query.filter_by(entidad=entidad, registro_id=identificador).count(), 4)
                baja = self.client.delete(f"/{tipo}/{identificador}/autores", json={"autores": [self.autores[1]]}, headers=self.headers)
                self.assertEqual(baja.status_code, 400)
                self.assertEqual(len(self.client.get(f"/{tipo}/{identificador}", headers=self.headers).get_json()["autores"]), 1)

    def test_solo_investigador_solo_becario_y_ambos(self):
        for tipo in ("reuniones", "revistas"):
            for indice, autores in enumerate(([self.autores[0]], [self.autores[1]], self.autores[:2])):
                payload = self.payload(tipo)
                payload.update(autores=autores, titulo_trabajo=f"Estudio de sistemas {indice}")
                respuesta = self.client.post(f"/{tipo}", json=payload, headers=self.headers)
                self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
                self.assertEqual(len(respuesta.get_json()["autores"]), len(autores))

    def test_busqueda_global_por_investigador_y_becario(self):
        self.crear("reuniones")
        self.crear("revistas")
        for nombre in ("Luis Becario", "Ana Investigadora"):
            resultados = SearchService.search(nombre)
            trabajos = [r for r in resultados if r["tipo"].startswith("Trabajo en")]
            self.assertEqual(len(trabajos), 2)
            for trabajo in trabajos:
                self.assertEqual(len(trabajo["extra"]["autores"]), 2)
                self.assertNotIn("investigadores", trabajo["extra"])

    def test_rechaza_autores_invalidos_sin_persistir_cambios_parciales(self):
        invalidos = (None, {}, [], [self.autores[0]] * 2, [{"id": 99, "rol": "becario"}],
                     [{"id": True, "rol": "investigador"}], [{"id": 1, "rol": "externo"}], [{"id": 1, "rol": "personal"}], [{"id": 1, "rol": []}],
                     [{"id": 2, "rol": "investigador"}], [{"id": 3, "rol": "investigador"}])
        for tipo in ("reuniones", "revistas"):
            identificador = self.crear(tipo)
            for autores in invalidos:
                with self.subTest(tipo=tipo, autores=autores):
                    payload = self.payload(tipo)
                    payload.update(titulo_trabajo="Trabajo que no debe persistirse", autores=autores)
                    self.assertIn(self.client.post(f"/{tipo}", json=payload, headers=self.headers).status_code, (400, 404))
                    respuesta = self.client.put(f"/{tipo}/{identificador}", json={"autores": autores, "titulo_trabajo": "Cambio inválido"}, headers=self.headers)
                    self.assertIn(respuesta.status_code, (400, 404))
                    detalle = self.client.get(f"/{tipo}/{identificador}", headers=self.headers).get_json()
                    self.assertEqual(detalle["titulo_trabajo"], "Estudio de sistemas")
                    self.assertEqual(len(detalle["autores"]), 2)

    def test_alta_revista_sin_autores_no_persiste_y_admite_reintento(self):
        payload = self.payload("revistas")
        payload["autores"] = []

        rechazo = self.client.post("/revistas", json=payload, headers=self.headers)

        self.assertEqual(rechazo.status_code, 400)
        self.assertIn("autores", rechazo.get_json()["error"]["details"]["fields"])
        self.assertEqual(TrabajosRevistasReferato.query.count(), 0)

        payload["autores"] = self.autores
        reintento = self.client.post("/revistas", json=payload, headers=self.headers)

        self.assertEqual(reintento.status_code, 201, reintento.get_json())
        self.assertEqual(TrabajosRevistasReferato.query.count(), 1)

    def test_rechaza_personal_existente_activo_en_alta_edicion_baja_y_filtro(self):
        # Personal existe y está activo; su categoría, no su estado, lo excluye.
        personal = {"id": 1, "rol": "personal"}
        for tipo in ("reuniones", "revistas"):
            identificador = self.crear(tipo)
            for autores in ([personal], [*self.autores, personal]):
                payload = self.payload(tipo)
                payload.update(titulo_trabajo="Alta excluida", autores=autores)
                self.assertEqual(self.client.post(f"/{tipo}", json=payload, headers=self.headers).status_code, 400)
                self.assertEqual(self.client.put(f"/{tipo}/{identificador}", json={"titulo_trabajo": "Edición excluida", "autores": autores}, headers=self.headers).status_code, 400)
            self.assertEqual(self.client.delete(f"/{tipo}/{identificador}/autores", json={"autores": [personal]}, headers=self.headers).status_code, 400)
            self.assertEqual(self.client.get(f"/{tipo}?autor_rol=personal&autor_id=1", headers=self.headers).status_code, 400)
            detalle = self.client.get(f"/{tipo}/{identificador}", headers=self.headers).get_json()
            self.assertEqual(detalle["titulo_trabajo"], "Estudio de sistemas")
            self.assertEqual({a["rol"] for a in detalle["autores"]}, {"investigador", "becario"})

    def test_conserva_y_permite_quitar_asociaciones_historicas_inactivas(self):
        identificador = self.crear("reuniones")
        becario = db.session.get(Becario, 1)
        becario.soft_delete(7)
        db.session.commit()
        detalle = self.client.put(f"/reuniones/{identificador}", json={"autores": self.autores}, headers=self.headers)
        self.assertEqual(detalle.status_code, 200)
        self.assertFalse(next(a for a in detalle.get_json()["autores"] if a["rol"] == "becario")["activo"])
        baja = self.client.put(f"/reuniones/{identificador}", json={"autores": [self.autores[0]]}, headers=self.headers)
        self.assertEqual(baja.status_code, 200)

    def test_permisos_y_baja_del_trabajo(self):
        identificador = self.crear("reuniones")
        with patch("modules.shared.services.middleware.AuthService.verify_token", return_value={"sub": "7", "rol": "LECTURA"}):
            self.assertEqual(self.client.get(f"/reuniones/{identificador}", headers=self.headers).status_code, 200)
            for metodo, url, body in (("post", "/reuniones", self.payload("reuniones")), ("put", f"/reuniones/{identificador}", {"autores": []}), ("delete", f"/reuniones/{identificador}/autores", {"autores": self.autores})):
                self.assertEqual(getattr(self.client, metodo)(url, json=body, headers=self.headers).status_code, 403)
        self.assertEqual(self.client.put(f"/reuniones/{identificador}", json={"autores": []}).status_code, 401)
        self.client.delete(f"/reuniones/{identificador}", headers=self.headers)
        self.assertEqual(self.client.put(f"/reuniones/{identificador}", json={"autores": []}, headers=self.headers).status_code, 409)

    def test_rollback_si_falla_auditoria(self):
        for tipo in ("reuniones", "revistas"):
            identificador = self.crear(tipo)
            with patch("modules.produccion.services.trabajo_autores_service.AuditoriaService.registrar_evento_relacion", side_effect=RuntimeError("fallo de prueba")):
                respuesta = self.client.put(f"/{tipo}/{identificador}", json={"autores": [self.autores[0]], "titulo_trabajo": "Cambio transaccional"}, headers=self.headers)
                self.assertEqual(respuesta.status_code, 500)
            detalle = self.client.get(f"/{tipo}/{identificador}", headers=self.headers).get_json()
            self.assertEqual(detalle["titulo_trabajo"], "Estudio de sistemas")
            self.assertEqual(len(detalle["autores"]), 2)

    def test_constraints_integridad_referencial_y_duplicados(self):
        for tipo, modelo in (("reuniones", TrabajoReunionAutor), ("revistas", TrabajoRevistaAutor)):
            identificador = self.crear(tipo)
            for campos in ({}, {"becario_id": 1, "investigador_id": 1}, {"becario_id": 99}, {"becario_id": 1}):
                db.session.add(modelo(trabajo_id=identificador, **campos))
                with self.assertRaises(IntegrityError):
                    db.session.commit()
                db.session.rollback()

    def test_snapshot_y_excel_con_autores_inmutables(self):
        self.crear("reuniones")
        self.crear("revistas")
        memoria = Memoria(grupo_utn_id=1, periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31), created_by=7)
        db.session.add(memoria)
        db.session.flush()
        version = MemoriaVersion(memoria_id=memoria.id, numero_version=1, fecha_apertura=datetime(2026, 1, 1), estado=EstadoMemoria.CERRADA, created_by=7)
        db.session.add(version)
        db.session.flush()
        version.contexto_institucional = snapshot_contexto_institucional(version)
        reuniones = TrabajoReunionCientificaService.snapshot_para_memoria_version(version, 7)
        revistas = TrabajosRevistasReferatoService.snapshot_para_memoria_version(version, 7)
        db.session.commit()
        for modelo in (Investigador, Becario):
            db.session.get(modelo, 1).nombre_apellido = "Nombre posterior"
        db.session.get(TipoPersonal, 1).nombre = "Categoría posterior"
        db.session.commit()
        for snapshot in (*reuniones, *revistas):
            self.assertEqual([a["nombre_apellido"] for a in snapshot.autores], ["Ana Investigadora", "Luis Becario"])
            self.assertEqual(snapshot.autores[1]["tipo"], "Becario")
        fuentes = {clave: [] for clave in ("investigadores", "becarios", "personal", "proyectos", "participaciones", "visitas", "articulos", "documentacion", "registros", "distinciones", "transferencias", "actividades", "erogaciones", "equipamiento", "becas", "planificaciones")}
        fuentes.update(memoria=memoria, version=version, trabajos_reunion=[s.serialize() for s in reuniones], trabajos_revista=[s.serialize() for s in revistas])
        # Exercise the full XLSX writer with the frozen author snapshots.
        with patch.object(ExportService, "_build_memoria_snapshot_sources", return_value=fuentes):
            contenido = ExportService.generar_excel_memoria(memoria.id, version.id)
        workbook = load_workbook(BytesIO(contenido.getvalue()))
        textos = [str(celda.value) for hoja in workbook for fila in hoja for celda in fila if celda.value is not None]
        self.assertGreaterEqual(sum("Luis Becario (Becario)" in texto for texto in textos), 2)
        self.assertFalse(any("Eva Profesional" in texto for texto in textos))
        self.assertFalse(any("Nombre posterior" in texto for texto in textos))


if __name__ == "__main__":
    unittest.main()
