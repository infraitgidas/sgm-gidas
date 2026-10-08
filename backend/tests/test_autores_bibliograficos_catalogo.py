import unittest
from datetime import date, datetime
from unittest.mock import patch

from flask import Flask

from extension import db
from modules import models_registry  # noqa: F401
from modules.auth.models.usuario import RolUsuario, Usuario
from modules.auth.models.usuario_grupo_utn import UsuarioGrupoUtn
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.memorias.models.memorias import EstadoMemoria, Memoria, MemoriaVersion
from modules.produccion.models.documentacion_autores import (
    Autor,
    DocumentacionBibliografica,
    DocumentacionBibliograficaAutorMemoriaVersion,
    DocumentacionBibliograficaMemoriaVersion,
)
from modules.produccion.routes.autores_rutas import autor_bp
from modules.produccion.routes.documentacion_rutas import documentacion_bibliografica_bp
from modules.shared.models.auditoria_campo import AuditoriaCampo
from modules.shared.services.tenant_request import register_tenant_request_scope
from modules.shared.services.tenant_scope import register_tenant_orm_policy


class AutoresBibliograficosCatalogoTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(autor_bp, url_prefix="/api/v1/autores")
        self.app.register_blueprint(
            documentacion_bibliografica_bp,
            url_prefix="/api/v1/documentacion-bibliografica",
        )
        register_tenant_request_scope(self.app)
        register_tenant_orm_policy()
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add_all([
            RolUsuario(id=1, nombre="ADMIN"),
            RolUsuario(id=2, nombre="GESTOR"),
            RolUsuario(id=3, nombre="LECTURA"),
            Usuario(id=1, nombre_usuario="admin", mail="admin@example.test", id_rol=1, contrasena="unused", primer_login=False),
            Usuario(id=2, nombre_usuario="gestor", mail="gestor@example.test", id_rol=2, contrasena="unused", primer_login=False),
            Usuario(id=3, nombre_usuario="lectura", mail="lectura@example.test", id_rol=3, contrasena="unused", primer_login=False),
            Usuario(id=4, nombre_usuario="externo", mail="externo@example.test", id_rol=1, contrasena="unused", primer_login=False),
            GrupoInvestigacionUtn(id=1, nombre_sigla_grupo="UCT 1", nombre_unidad_academica="Regional", objetivo_desarrollo="Investigación", mail="uct1@example.test"),
            GrupoInvestigacionUtn(id=2, nombre_sigla_grupo="UCT 2", nombre_unidad_academica="Regional", objetivo_desarrollo="Investigación", mail="uct2@example.test"),
        ])
        db.session.flush()
        db.session.add_all([
            UsuarioGrupoUtn(usuario_id=user_id, grupo_utn_id=group_id, created_by=1)
            for user_id, group_id in ((1, 1), (2, 1), (3, 1), (4, 2))
        ])
        db.session.add_all([
            Autor(id=1, grupo_utn_id=1, nombre_apellido="Ana Pérez", created_by=1),
            Autor(id=2, grupo_utn_id=2, nombre_apellido="Otra UCT", created_by=4),
            Autor(id=3, grupo_utn_id=1, nombre_apellido="Sin vínculos", created_by=1),
            DocumentacionBibliografica(id=1, titulo="Libro", editorial="Editorial", anio=2025, fecha=date(2025, 3, 1), grupo_id=1, created_by=1),
            Memoria(id=1, grupo_utn_id=1, periodo_inicio=date(2025, 1, 1), periodo_fin=date(2025, 12, 31)),
        ])
        db.session.flush()
        documentacion = db.session.get(DocumentacionBibliografica, 1)
        documentacion.autores.append(db.session.get(Autor, 1))
        db.session.add(MemoriaVersion(id=1, memoria_id=1, numero_version=1, fecha_apertura=datetime(2025, 1, 1), estado=EstadoMemoria.CERRADA))
        db.session.flush()
        snapshot = DocumentacionBibliograficaMemoriaVersion(
            id=1, memoria_version_id=1, documentacion_bibliografica_id=1,
            titulo="Libro", editorial="Editorial", anio=2025,
            fecha=date(2025, 3, 1), grupo_id=1,
        )
        db.session.add(snapshot)
        db.session.flush()
        db.session.add(DocumentacionBibliograficaAutorMemoriaVersion(
            documentacion_memoria_version_id=1, autor_id=1, nombre_apellido="Ana Pérez"
        ))
        db.session.commit()
        db.session.remove()
        self.auth_patch = patch(
            "modules.auth.services.auth_service.AuthService.verify_token",
            side_effect=lambda token: {"sub": token},
        )
        self.auth_patch.start()
        self.client = self.app.test_client()

    def tearDown(self):
        self.auth_patch.stop()
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def request(self, method, path, user_id=1, **kwargs):
        return self.client.open(path, method=method, headers={"Authorization": f"Bearer {user_id}"}, **kwargs)

    def test_nombre_real_se_audita_una_vez_y_memoria_cerrada_conserva_snapshot(self):
        response = self.request("PUT", "/api/v1/autores/1", user_id=2, json={"nombre_apellido": "Ana María Pérez"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["updated_by"], 2)
        self.assertEqual(response.json["nombre_apellido"], "Ana María Pérez")
        self.assertEqual(self.request("GET", "/api/v1/documentacion-bibliografica/1").json["autores"][0]["nombre_apellido"], "Ana María Pérez")
        history = self.request("GET", "/api/v1/autores/1/historial").json
        self.assertEqual(len(history), 1)
        self.assertEqual((history[0]["campo"], history[0]["valor_anterior"], history[0]["valor_nuevo"]), ("nombre_apellido", "Ana Pérez", "Ana María Pérez"))
        self.assertEqual(history[0]["usuario_nombre"], "gestor")
        self.assertEqual(self.request("GET", "/api/v1/documentacion-bibliografica/1/historial").json, [])
        db.session.remove()
        self.assertEqual(db.session.get(DocumentacionBibliograficaAutorMemoriaVersion, 1).nombre_apellido, "Ana Pérez")

        unchanged = self.request("PUT", "/api/v1/autores/1", user_id=2, json={"nombre_apellido": " Ana María Pérez "})
        self.assertEqual(unchanged.status_code, 200)
        self.assertEqual(len(self.request("GET", "/api/v1/autores/1/historial").json), 1)

    def test_alta_conserva_el_contrato_de_documentacion_y_asigna_uct(self):
        response = self.request("POST", "/api/v1/autores/", user_id=2, json={"nombre_apellido": "Laura Gómez"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["grupo_utn_id"], 1)
        self.assertEqual(response.json["created_by"], 2)
        self.assertIn(response.json["id"], [item["id"] for item in self.request("GET", "/api/v1/autores/").json])
        other_uct = self.request("POST", "/api/v1/autores/", user_id=4, json={"nombre_apellido": "Laura Gómez"})
        self.assertEqual(other_uct.status_code, 201)
        self.assertEqual(other_uct.json["grupo_utn_id"], 2)

    def test_baja_vinculada_bloqueada_y_baja_libre_logica(self):
        self.assertEqual(self.request("DELETE", "/api/v1/autores/1").status_code, 409)
        self.assertIsNone(db.session.get(Autor, 1).deleted_at)
        response = self.request("DELETE", "/api/v1/autores/3", user_id=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in self.request("GET", "/api/v1/autores/").json], [1])
        self.assertEqual([item["id"] for item in self.request("GET", "/api/v1/autores/?activos=all").json], [1, 3])
        self.assertEqual(self.request("PUT", "/api/v1/autores/3", json={"nombre_apellido": "Otro nombre"}).status_code, 409)
        self.assertEqual(self.request("DELETE", "/api/v1/autores/3").status_code, 409)

    def test_baja_logica_permitida_si_solo_hay_documentacion_inactiva(self):
        self.assertEqual(self.request("DELETE", "/api/v1/documentacion-bibliografica/1", user_id=2).status_code, 200)
        response = self.request("DELETE", "/api/v1/autores/1", user_id=2)
        self.assertEqual(response.status_code, 200)
        db.session.remove()
        autor = db.session.get(Autor, 1)
        self.assertIsNotNone(autor.deleted_at)
        self.assertEqual(autor.deleted_by, 2)
        self.assertEqual([documento.id for documento in autor.libros], [1])
        self.assertEqual(db.session.get(DocumentacionBibliograficaAutorMemoriaVersion, 1).nombre_apellido, "Ana Pérez")
        self.assertEqual([item["id"] for item in self.request("GET", "/api/v1/autores/").json], [3])

    def test_uct_y_permisos_protegen_lista_detalle_historial_y_escrituras(self):
        self.assertEqual([item["id"] for item in self.request("GET", "/api/v1/autores/?activos=all").json], [1, 3])
        for method, path, body in (
            ("GET", "/api/v1/autores/2", None),
            ("GET", "/api/v1/autores/2/historial", None),
            ("PUT", "/api/v1/autores/2", {"nombre_apellido": "Intrusión"}),
            ("DELETE", "/api/v1/autores/2", None),
        ):
            response = self.request(method, path, json=body) if body else self.request(method, path)
            self.assertEqual(response.status_code, 404)
        self.assertEqual([item["id"] for item in self.request("GET", "/api/v1/autores/?activos=all", user_id=4).json], [2])
        for method, path, body in (
            ("POST", "/api/v1/autores/", {"nombre_apellido": "Nuevo Autor"}),
            ("PUT", "/api/v1/autores/1", {"nombre_apellido": "Otro Autor"}),
            ("DELETE", "/api/v1/autores/3", None),
        ):
            response = self.request(method, path, user_id=3, json=body) if body else self.request(method, path, user_id=3)
            self.assertEqual(response.status_code, 403)

    def test_ruta_alternativa_de_vinculacion_solo_audita_documentacion(self):
        self.assertEqual(self.request("POST", "/api/v1/autores/3/libros", json={"libro_id": 1}).status_code, 200)
        self.assertEqual(self.request("DELETE", "/api/v1/autores/3/libros/1").status_code, 200)
        self.assertEqual(self.request("GET", "/api/v1/autores/3/historial").json, [])
        history = self.request("GET", "/api/v1/documentacion-bibliografica/1/historial").json
        self.assertEqual(len(history), 2)
        self.assertEqual([item["valor_nuevo"]["accion"] for item in history], ["desvincular", "vincular"])

    def test_historial_documentacion_excluye_cambios_de_autor_atribuidos_por_error(self):
        db.session.add_all([
            AuditoriaCampo(entidad="documentacion_bibliografica", registro_id=1,
                           campo="nombre_apellido", valor_anterior="Ana Pérez", valor_nuevo="Ana María Pérez", usuario_id=2),
            AuditoriaCampo(entidad="documentacion_bibliografica", registro_id=1,
                           campo="titulo", valor_anterior="Libro", valor_nuevo="Libro corregido", usuario_id=2),
        ])
        db.session.commit()
        db.session.remove()
        history = self.request("GET", "/api/v1/documentacion-bibliografica/1/historial").json
        self.assertEqual([item["campo"] for item in history], ["titulo"])


if __name__ == "__main__":
    unittest.main()
