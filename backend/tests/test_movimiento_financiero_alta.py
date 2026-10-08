import unittest
from datetime import date
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError

from app import create_app
from config import Config
from extension import db
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.dashboard.services.dashboard_service import DashboardService
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.memorias.services.exportacion_service_impl import ExportService
from modules.recursos.models.movimiento_financiero import (
    CategoriaErogacion, MovimientoFinanciero, MovimientoMemoriaVersion,
)
from modules.recursos.models.equipamiento import Equipamiento
from modules.recursos.models.tipo_cambio import TipoCambio
from modules.recursos.clients.bcra_client import CotizacionBCRA
from modules.recursos.services.movimiento_financiero_service import MovimientoFinancieroService
from modules.recursos.services.saldo_financiero_service import SaldoFinancieroService
from modules.recursos.services.tipo_cambio_service import TipoCambioService
from modules.shared.exceptions import ConflictError, ValidationError
from modules.shared.models.auditoria_campo import AuditoriaCampo
from tools.seed_testing_data import _seed_group


class MovimientoFinancieroAltaTestCase(unittest.TestCase):
    def setUp(self):
        config = type(
            "MovimientoTestConfig", (Config,),
            {"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"},
        )
        with patch("app.get_config_class", return_value=config):
            self.app = create_app()
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.grupo = GrupoInvestigacionUtn(
            mail="gidas@example.org", nombre_unidad_academica="UTN",
            objetivo_desarrollo="Investigación", nombre_sigla_grupo="GIDAS",
        )
        self.fuente = FuenteFinanciamiento(nombre="UTN")
        self.categoria = CategoriaErogacion(codigo="CORRIENTE", nombre="Corriente")
        db.session.add_all([self.grupo, self.fuente, self.categoria])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _payload(self, tipo, **changes):
        payload = {
            "grupo_utn_id": self.grupo.id,
            "fecha": "2026-09-01",
            "tipo_movimiento": tipo,
            "moneda": "ARS",
            "monto": "100.25",
            "fuente_financiamiento_id": self.fuente.id,
        }
        payload.update(changes)
        return payload

    def test_usd_usa_cotizacion_anterior_y_conserva_snapshot(self):
        cotizacion = TipoCambio(moneda_origen="USD", moneda_destino="ARS",
                                fecha_cotizacion=date(2026, 8, 31), valor=Decimal("1538.390000"),
                                serie_bcra=TipoCambioService.serie(), fuente="BCRA")
        db.session.add(cotizacion)
        db.session.commit()
        ingreso = MovimientoFinancieroService.create(
            self._payload("INGRESO", moneda="USD", monto="1000.00"), 1,
        )
        self.assertEqual(ingreso["monto"], "1000.00")
        self.assertEqual(ingreso["monto_equivalente_ars"], "1538390.00")
        self.assertEqual(ingreso["tipo_cambio"]["fecha_cotizacion"], "2026-08-31")
        self.assertEqual(SaldoFinancieroService.calcular(self.grupo.id).saldo_disponible,
                         Decimal("1538390.00"))
        cotizacion.valor = Decimal("1600")
        db.session.commit()
        guardado = MovimientoFinancieroService.get_by_id(ingreso["id"])
        self.assertEqual(guardado["tipo_cambio_aplicado"], "1538.390000")
        self.assertEqual(guardado["monto_equivalente_ars"], "1538390.00")

    def test_usd_sin_cotizacion_anterior_se_rechaza(self):
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.create(self._payload("INGRESO", moneda="USD"), 1)

    def test_usd_consolida_saldos_y_memoria_sin_recalcular_cotizacion(self):
        db.session.add(TipoCambio(moneda_origen="USD", moneda_destino="ARS",
                                  fecha_cotizacion=date(2026, 9, 1), valor=Decimal("2.500000"),
                                  serie_bcra=TipoCambioService.serie(), fuente="BCRA"))
        db.session.commit()
        ingreso = MovimientoFinancieroService.create(
            self._payload("INGRESO", moneda="USD", monto="100.00"), 1)
        egreso = MovimientoFinancieroService.create(
            self._payload("EGRESO", moneda="USD", monto="10.00",
                          categoria_erogacion_id=self.categoria.id), 1)
        self.assertEqual(SaldoFinancieroService.calcular(self.grupo.id).saldo_disponible,
                         Decimal("225.00"))
        self.assertEqual(SaldoFinancieroService.saldo_de_fuente(self.grupo.id, self.fuente.id),
                         Decimal("225.00"))
        resumen = DashboardService.get_resumen()["resumen"]
        self.assertEqual(resumen["total_ingresos"], "250.00")
        self.assertEqual(resumen["egresos_corrientes"], "25.00")
        version = SimpleNamespace(id=83, memoria=SimpleNamespace(
            grupo_utn_id=self.grupo.id,
            periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31),
        ))
        MovimientoFinancieroService.snapshot_para_memoria_version(version, 1)
        db.session.commit()
        foto = MovimientoMemoriaVersion.query.filter_by(
            memoria_version_id=83, movimiento_id=egreso["id"]).one()
        self.assertEqual(foto.monto, Decimal("10.00"))
        self.assertEqual(foto.monto_equivalente_ars, Decimal("25.00"))
        self.assertEqual(foto.tipo_cambio_aplicado, Decimal("2.500000"))
        actualizado = MovimientoFinancieroService.update(ingreso["id"], {"monto": "101.00"}, 1)
        self.assertEqual(actualizado["tipo_cambio_aplicado"], "2.500000")
        self.assertEqual(actualizado["monto_equivalente_ars"], "252.50")
        self.assertEqual(foto.monto_equivalente_ars, Decimal("25.00"))
        with self.assertRaises(ValidationError):
            MovimientoFinancieroService.update(ingreso["id"], {"fecha": "2026-09-02"}, 1)

    def test_ars_no_consulta_tipo_cambio(self):
        with patch.object(TipoCambioService, "obtener_vigente_para_fecha") as buscar:
            ingreso = MovimientoFinancieroService.create(self._payload("INGRESO"), 1)
        buscar.assert_not_called()
        self.assertIsNone(ingreso["tipo_cambio_id"])
        self.assertEqual(ingreso["monto_equivalente_ars"], "100.25")

    def test_sincronizacion_es_idempotente_y_no_inventa_fines_de_semana(self):
        cliente = SimpleNamespace(
            serie=TipoCambioService.serie(), verificar_variable=lambda: None,
            consultar_tipo_cambio=lambda _desde, _hasta: [
                CotizacionBCRA(date(2026, 9, 25), Decimal("1538.39"), 4),
                CotizacionBCRA(date(2026, 9, 28), Decimal("1540.10"), 4),
            ],
        )
        primero = TipoCambioService.sincronizar(cliente, hoy=date(2026, 9, 28))
        segundo = TipoCambioService.sincronizar(cliente, hoy=date(2026, 9, 28))
        self.assertEqual((primero["inserted"], segundo["inserted"]), (2, 0))
        self.assertEqual(TipoCambio.query.count(), 2)
        self.assertEqual(TipoCambioService.obtener_vigente_para_fecha(date(2026, 9, 26)).fecha_cotizacion,
                         date(2026, 9, 25))

    def test_sincronizacion_fallida_no_persiste_cambios(self):
        def fallar(_desde, _hasta):
            raise RuntimeError("BCRA unavailable")
        cliente = SimpleNamespace(serie=TipoCambioService.serie(),
                                  verificar_variable=lambda: None, consultar_tipo_cambio=fallar)
        with self.assertRaises(RuntimeError):
            TipoCambioService.sincronizar(cliente, hoy=date(2026, 9, 28))
        self.assertEqual(TipoCambio.query.count(), 0)

    def test_semilla_usa_la_uct_activa_en_vez_de_crear_un_grupo_invisible(self):
        self.assertEqual(_seed_group().id, self.grupo.id)
        self.assertEqual(GrupoInvestigacionUtn.query.count(), 1)

    def test_numera_por_grupo_y_separa_id_de_numero_visible(self):
        primero = MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        segundo = MovimientoFinancieroService.create(
            self._payload("EGRESO", categoria_erogacion_id=self.categoria.id), 1,
        )
        self.assertEqual([primero["numero_movimiento"], segundo["numero_movimiento"]], [1, 2])
        self.assertEqual(primero["monto"], "100.25")
        self.assertEqual(primero["moneda"], "ARS")
        self.assertEqual(MovimientoFinanciero.query.count(), 2)

    def test_listado_y_saldo_separan_grupos(self):
        otro_grupo = GrupoInvestigacionUtn(
            mail="otro@example.org", nombre_unidad_academica="UTN",
            objetivo_desarrollo="Investigación", nombre_sigla_grupo="OTRO",
        )
        db.session.add(otro_grupo)
        db.session.commit()
        MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        MovimientoFinancieroService.create({
            **self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id),
            "grupo_utn_id": otro_grupo.id, "monto": "300.00",
        }, 1)
        movimientos = MovimientoFinancieroService.get_all({"grupo_utn_id": self.grupo.id})
        self.assertEqual(len(movimientos), 1)
        self.assertEqual(movimientos[0]["numero_movimiento"], 1)
        self.assertEqual(SaldoFinancieroService.calcular(self.grupo.id).saldo_disponible, Decimal("100.25"))

    def test_saldos_por_fuente_incluyen_egresos_y_excluyen_bajas_y_otros_grupos(self):
        otra_fuente = FuenteFinanciamiento(nombre="Provincia")
        otro_grupo = GrupoInvestigacionUtn(
            mail="otro@example.org", nombre_unidad_academica="UTN",
            objetivo_desarrollo="Investigación", nombre_sigla_grupo="OTRO",
        )
        db.session.add_all([otra_fuente, otro_grupo])
        db.session.commit()
        MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        MovimientoFinancieroService.create(
            self._payload("INGRESO", monto="50.10", fuente_financiamiento_id=otra_fuente.id), 1,
        )
        eliminado = MovimientoFinancieroService.create(
            self._payload("INGRESO", monto="5.00", fuente_financiamiento_id=otra_fuente.id), 1,
        )
        MovimientoFinancieroService.create(
            self._payload("EGRESO", monto="25.00", categoria_erogacion_id=self.categoria.id), 1,
        )
        MovimientoFinancieroService.create({
            **self._payload("INGRESO", monto="300.00", fuente_financiamiento_id=self.fuente.id),
            "grupo_utn_id": otro_grupo.id,
        }, 1)
        MovimientoFinancieroService.delete(eliminado["id"], 1)

        self.assertEqual(SaldoFinancieroService.saldos_por_fuente(self.grupo.id), [
            {"fuente_id": self.fuente.id, "fuente_nombre": "UTN",
             "total_ingresos": "100.25", "total_egresos": "25.00",
             "saldo_disponible": "75.25", "cantidad_movimientos": 2},
            {"fuente_id": otra_fuente.id, "fuente_nombre": "Provincia",
             "total_ingresos": "50.10", "total_egresos": "0.00",
             "saldo_disponible": "50.10", "cantidad_movimientos": 1},
        ])

    def test_no_acepta_numero_elegido_por_cliente(self):
        with self.assertRaises(ValidationError):
            MovimientoFinancieroService.create(
                self._payload(
                    "INGRESO", fuente_financiamiento_id=self.fuente.id,
                    numero_movimiento=99,
                ), 1,
            )
        self.assertEqual(MovimientoFinanciero.query.count(), 0)

    def test_restriccion_de_base_impide_numeros_duplicados(self):
        MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        db.session.add(MovimientoFinanciero(
            grupo_utn_id=self.grupo.id,
            numero_movimiento=1,
            tipo_movimiento="INGRESO",
            monto="1.00",
            moneda="ARS",
            fecha=self.grupo.created_at.date(),
            fuente_financiamiento_id=self.fuente.id,
        ))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(MovimientoFinanciero.query.count(), 1)

    def test_exige_relacion_segun_tipo(self):
        for payload in (
            self._payload("INGRESO", fuente_financiamiento_id=None),
            self._payload("EGRESO"),
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id,
                          categoria_erogacion_id=self.categoria.id),
            self._payload("EGRESO", fuente_financiamiento_id=None,
                          categoria_erogacion_id=self.categoria.id),
        ):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                MovimientoFinancieroService.create(payload, 1)
        self.assertEqual(MovimientoFinanciero.query.count(), 0)

    def test_saldo_y_edicion_de_egreso_respetan_limites(self):
        MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.create(
                self._payload("EGRESO", monto="100.26",
                              categoria_erogacion_id=self.categoria.id), 1,
            )
        egreso = MovimientoFinancieroService.create(
            self._payload("EGRESO", categoria_erogacion_id=self.categoria.id), 1,
        )
        resumen = SaldoFinancieroService.calcular(self.grupo.id)
        self.assertEqual(resumen.serialize(), {
            "moneda": "ARS", "total_ingresos": "100.25",
            "total_egresos": "100.25", "saldo_disponible": "0.00",
            "cantidad_movimientos": 2,
        })
        actualizado = MovimientoFinancieroService.update(egreso["id"], {"monto": "60.00"}, 1)
        self.assertEqual(actualizado["monto"], "60.00")
        self.assertEqual(SaldoFinancieroService.calcular(self.grupo.id).saldo_disponible, Decimal("40.25"))
        self.assertEqual(AuditoriaCampo.query.filter_by(
            entidad="movimiento_financiero", registro_id=egreso["id"], campo="monto"
        ).count(), 1)
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.update(egreso["id"], {"monto": "100.26"}, 1)
        with self.assertRaises(ValidationError):
            MovimientoFinancieroService.update(egreso["id"], {"tipo_movimiento": "INGRESO"}, 1)

    def test_egreso_respeta_saldo_de_su_fuente(self):
        otra_fuente = FuenteFinanciamiento(nombre="Provincia")
        db.session.add(otra_fuente)
        db.session.commit()
        MovimientoFinancieroService.create(self._payload("INGRESO", monto="100.00"), 1)
        MovimientoFinancieroService.create(self._payload(
            "INGRESO", monto="20.00", fuente_financiamiento_id=otra_fuente.id,
        ), 1)
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.create(self._payload(
                "EGRESO", monto="25.00", fuente_financiamiento_id=otra_fuente.id,
                categoria_erogacion_id=self.categoria.id,
            ), 1)
        egreso = MovimientoFinancieroService.create(self._payload(
            "EGRESO", monto="50.00", categoria_erogacion_id=self.categoria.id,
        ), 1)
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.update(
                egreso["id"], {"fuente_financiamiento_id": otra_fuente.id}, 1,
            )
        self.assertEqual(SaldoFinancieroService.saldo_de_fuente(self.grupo.id, self.fuente.id), Decimal("50.00"))
        self.assertEqual(SaldoFinancieroService.saldo_de_fuente(self.grupo.id, otra_fuente.id), Decimal("20.00"))

    def test_ingreso_no_puede_abandonar_fuente_con_egresos_pendientes(self):
        otra_fuente = FuenteFinanciamiento(nombre="Provincia")
        db.session.add(otra_fuente)
        db.session.commit()
        ingreso = MovimientoFinancieroService.create(self._payload("INGRESO", monto="100.00"), 1)
        MovimientoFinancieroService.create(self._payload(
            "INGRESO", monto="100.00", fuente_financiamiento_id=otra_fuente.id,
        ), 1)
        MovimientoFinancieroService.create(self._payload(
            "EGRESO", monto="70.00", categoria_erogacion_id=self.categoria.id,
        ), 1)
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.update(
                ingreso["id"], {"fuente_financiamiento_id": otra_fuente.id}, 1,
            )
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.delete(ingreso["id"], 1)

    def test_equipamiento_unico_toma_monto_y_conserva_snapshot(self):
        equipo = Equipamiento(
            denominacion="Microscopio", descripcion_breve="Equipo de laboratorio",
            fecha_incorporacion=date(2026, 8, 1), monto_invertido=75.5,
            grupo_utn_id=self.grupo.id,
        )
        db.session.add(equipo)
        db.session.commit()
        MovimientoFinancieroService.create(self._payload("INGRESO", monto="200.00"), 1)
        egreso = MovimientoFinancieroService.create(self._payload(
            "EGRESO", monto="1.00", categoria_erogacion_id=self.categoria.id,
            equipamiento_id=equipo.id,
        ), 1)
        self.assertEqual(egreso["monto"], "75.50")
        self.assertEqual(egreso["equipamiento"]["denominacion"], "Microscopio")
        version = SimpleNamespace(id=82, memoria=SimpleNamespace(
            grupo_utn_id=self.grupo.id,
            periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31),
        ))
        MovimientoFinancieroService.snapshot_para_memoria_version(version, 1)
        db.session.commit()
        foto = MovimientoMemoriaVersion.query.filter_by(
            memoria_version_id=82, movimiento_id=egreso["id"]
        ).one()
        self.assertEqual(foto.equipamiento_denominacion, "Microscopio")
        self.assertEqual(MovimientoFinancieroService.equipamientos_disponibles(self.grupo.id), [])
        self.assertEqual(len(MovimientoFinancieroService.equipamientos_disponibles(
            self.grupo.id, egreso["id"]
        )), 1)
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.create(self._payload(
                "EGRESO", categoria_erogacion_id=self.categoria.id,
                equipamiento_id=equipo.id,
            ), 1)
        equipo.monto_invertido = 90.0
        equipo.denominacion = "Microscopio actualizado"
        db.session.commit()
        self.assertEqual(MovimientoFinancieroService.get_by_id(egreso["id"])["monto"], "75.50")
        self.assertEqual(foto.equipamiento_denominacion, "Microscopio")
        with self.assertRaises(ValidationError):
            MovimientoFinancieroService.update(egreso["id"], {"monto": "90.00"}, 1)
        desvinculado = MovimientoFinancieroService.update(
            egreso["id"], {"equipamiento_id": None, "monto": "80.00"}, 1,
        )
        self.assertIsNone(desvinculado["equipamiento_id"])
        self.assertEqual(desvinculado["monto"], "80.00")
        self.assertEqual(len(MovimientoFinancieroService.equipamientos_disponibles(self.grupo.id)), 1)

    def test_baja_de_ingreso_no_permite_saldo_negativo(self):
        ingreso = MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        egreso = MovimientoFinancieroService.create(
            self._payload("EGRESO", monto="25.00",
                          categoria_erogacion_id=self.categoria.id), 1,
        )
        with self.assertRaises(ConflictError):
            MovimientoFinancieroService.delete(ingreso["id"], 1)
        MovimientoFinancieroService.delete(egreso["id"], 1)
        self.assertEqual(SaldoFinancieroService.calcular(self.grupo.id).saldo_disponible, Decimal("100.25"))
        MovimientoFinancieroService.delete(ingreso["id"], 1)
        self.assertEqual(SaldoFinancieroService.calcular(self.grupo.id).serialize()["cantidad_movimientos"], 0)

    def test_snapshot_conserva_monto_y_categoria_tras_edicion(self):
        MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        egreso = MovimientoFinancieroService.create(
            self._payload("EGRESO", monto="25.00",
                          categoria_erogacion_id=self.categoria.id), 1,
        )
        version = SimpleNamespace(id=51, memoria=SimpleNamespace(
            grupo_utn_id=self.grupo.id,
            periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31),
        ))
        snapshots = MovimientoFinancieroService.snapshot_para_memoria_version(version, 1)
        db.session.commit()
        self.assertEqual(len(snapshots), 2)
        foto = MovimientoMemoriaVersion.query.filter_by(
            memoria_version_id=51, movimiento_id=egreso["id"],
        ).one()
        self.assertEqual(foto.categoria_erogacion_codigo, "CORRIENTE")
        MovimientoFinancieroService.update(egreso["id"], {"monto": "30.00"}, 1)
        db.session.expire_all()
        fotos = MovimientoFinancieroService.obtener_snapshots_por_memoria_version(51)
        egreso_foto = next(item for item in fotos if item["movimiento_id"] == egreso["id"])
        self.assertEqual(egreso_foto["monto"], "25.00")
        self.assertEqual(egreso_foto["categoria_erogacion_codigo"], "CORRIENTE")

    def test_dashboard_y_exportacion_usan_movimientos(self):
        MovimientoFinancieroService.create(
            self._payload("INGRESO", fuente_financiamiento_id=self.fuente.id), 1,
        )
        MovimientoFinancieroService.create(
            self._payload("EGRESO", monto="25.00",
                          categoria_erogacion_id=self.categoria.id), 1,
        )
        resumen = DashboardService.get_resumen()
        self.assertEqual(resumen["resumen"]["total_ingresos"], "100.25")
        self.assertEqual(resumen["resumen"]["total_egresos"], "25.00")
        self.assertEqual(resumen["resumen"]["saldo_financiero"], "75.25")
        self.assertEqual(resumen["resumen"]["egresos_corrientes"], "25.00")
        movimientos = ExportService._get_erogaciones(self.grupo.id)
        self.assertEqual(len(movimientos), 2)
        self.assertEqual(ExportService._clasificar_erogacion("CORRIENTE"), "corriente")

    def test_exportacion_de_memoria_separa_ingresos_y_categorias_de_egreso(self):
        memoria = SimpleNamespace(periodo_inicio=date(2026, 1, 1), periodo_fin=date(2026, 12, 31))
        version = SimpleNamespace(numero_version=1, contexto_institucional={
            "grupo": {
                "id": self.grupo.id,
                "nombre_unidad_academica": self.grupo.nombre_unidad_academica,
                "nombre_sigla_grupo": self.grupo.nombre_sigla_grupo,
                "mail": self.grupo.mail,
                "objetivo_desarrollo": self.grupo.objetivo_desarrollo,
            },
            "directivos": [],
            "programa_actividades": None,
            "anio_programa": 2027,
        })
        fuentes = {key: [] for key in (
            "investigadores", "becarios", "personal", "proyectos", "participaciones",
            "visitas", "articulos", "documentacion", "registros", "distinciones",
            "transferencias", "actividades", "erogaciones", "equipamiento", "becas",
            "planificaciones", "trabajos_reunion", "trabajos_revista",
        )}
        fuentes.update(memoria=memoria, version=version, erogaciones=[
            {"numero_movimiento": 1, "fecha": date(2026, 5, 1), "tipo_movimiento": "INGRESO",
             "monto": "100.25", "moneda": "ARS", "fuente_financiamiento_nombre": "UTN"},
            {"numero_movimiento": 2, "fecha": date(2026, 5, 2), "tipo_movimiento": "EGRESO",
             "monto": "25.00", "moneda": "ARS", "categoria_erogacion_codigo": "CORRIENTE",
             "categoria_erogacion_nombre": "Corriente"},
            {"numero_movimiento": 3, "fecha": date(2026, 5, 3), "tipo_movimiento": "EGRESO",
             "monto": "10.00", "moneda": "ARS", "categoria_erogacion_codigo": "CAPITAL",
             "categoria_erogacion_nombre": "Capital"},
            {"numero_movimiento": 4, "fecha": date(2026, 5, 4), "tipo_movimiento": "INGRESO",
             "monto": "100.00", "moneda": "USD", "monto_equivalente_ars": "200.00",
             "tipo_cambio_aplicado": "2.000000", "fuente_financiamiento_nombre": "UTN"},
        ])
        with patch.object(ExportService, "_build_memoria_snapshot_sources", return_value=fuentes):
            archivo = ExportService.generar_excel_memoria(1, 1)
        libro = load_workbook(BytesIO(archivo.getvalue()), data_only=True)
        celdas = [celda.value for hoja in libro for fila in hoja for celda in fila]
        self.assertIn("Erogaciones Corrientes", celdas)
        self.assertIn("Erogaciones de Capital", celdas)
        self.assertIn("Fuente de Financiamiento", celdas)
        self.assertIn("UTN", celdas)
        hoja = libro["Hoja1"]
        self.assertEqual(hoja["C309"].value, 300.25)  # ARS 100.25 + equivalente ARS 200.00 del USD
        self.assertEqual(hoja["E309"].value, 0)
        self.assertEqual(hoja["E310"].value, 25)  # Fuente no indicada: separada de UTN
        self.assertEqual(hoja["C318"].value, 0)  # No duplicar ingresos en capital
        self.assertEqual(hoja["E318"].value, 10)


if __name__ == "__main__":
    unittest.main()
