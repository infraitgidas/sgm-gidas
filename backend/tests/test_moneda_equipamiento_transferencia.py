import importlib.util
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from extension import db
from tests import test_movimiento_financiero_alta as fixtures
from modules.recursos.models.equipamiento import Equipamiento, EquipamientoMemoriaVersion
from modules.recursos.models.movimiento_financiero import MovimientoFinanciero
from modules.recursos.services.equipamiento_service import EquipamientoService
from modules.recursos.services.movimiento_financiero_service import MovimientoFinancieroService
from modules.transferencia.models.transferencia_socio import TipoContrato, TransferenciaSocioProductiva
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService as Transferencias
from modules.dashboard.services.dashboard_service import DashboardService
from modules.shared.exceptions import ValidationError


class MonedaDomainTest(unittest.TestCase):
    tearDown = fixtures.MovimientoFinancieroAltaTestCase.tearDown
    _payload = fixtures.MovimientoFinancieroAltaTestCase._payload

    def setUp(self):
        fixtures.MovimientoFinancieroAltaTestCase.setUp(self)
        self.tipo = TipoContrato(nombre="Asistencia técnica")
        db.session.add(self.tipo)
        db.session.commit()

    def equipo(self, **changes):
        payload = dict(denominacion="Equipo de prueba", descripcion_breve="Descripción del equipo",
                       fecha_incorporacion="2026-01-01", monto_invertido=123.45, grupo_utn_id=self.grupo.id)
        payload.update(changes)
        return EquipamientoService.create(payload, 1)

    def transferencia(self, **changes):
        payload = dict(denominacion="Convenio de prueba", demandante="Institución solicitante",
                       descripcion_actividad="Asistencia para el proyecto", monto=456.78,
                       fecha_inicio="2026-01-01", tipo_contrato_id=self.tipo.id, grupo_utn_id=self.grupo.id)
        payload.update(changes)
        return Transferencias.create(payload, 1)

    def test_alta_edicion_y_auditoria_en_ambos_modulos(self):
        for create, service in [(self.equipo, EquipamientoService), (self.transferencia, Transferencias)]:
            with self.subTest(service=service):
                creado = create(moneda="USD")
                self.assertEqual(creado["moneda"], "USD")
                campo = "monto_invertido" if service is EquipamientoService else "monto"
                monto = creado[campo]
                cambiado = service.update(creado["id"], {"moneda": "ARS"}, 1)
                self.assertEqual(cambiado[campo], monto)
                self.assertEqual(service.get_by_id(creado["id"])["moneda"], "ARS")
                eventos = service.get_historial(creado["id"])
                evento = next(item for item in eventos if item["campo"] == "moneda")
                self.assertEqual((evento["valor_anterior"], evento["valor_nuevo"]), ("USD", "ARS"))
                self.assertEqual(service.get_all()[0]["moneda"], "ARS")

    def test_compatibilidad_ars_y_rechazo_de_moneda_invalida(self):
        for create, service in [(self.equipo, EquipamientoService), (self.transferencia, Transferencias)]:
            creado = create()
            self.assertEqual(creado["moneda"], "ARS")
            for moneda in ["EUR", "usd", "", None, 1, True]:
                with self.assertRaises(ValidationError):
                    create(moneda=moneda)
                with self.assertRaises(ValidationError):
                    service.update(creado["id"], {"moneda": moneda}, 1)
                db.session.rollback()

    def test_foto_guarda_moneda_y_no_sigue_ediciones_posteriores(self):
        equipo = db.session.get(Equipamiento, self.equipo(moneda="USD")["id"])
        transferencia = db.session.get(TransferenciaSocioProductiva, self.transferencia(moneda="USD")["id"])
        version = SimpleNamespace(id=1)
        for path, service, registro in [
            ("modules.recursos.services.equipamiento_service", EquipamientoService, equipo),
            ("modules.transferencia.services.transferencia_service", Transferencias, transferencia),
        ]:
            with patch(f"{path}.consultar_entidades_memoria", return_value=[registro]), patch(
                f"{path}.estuvo_activo_en_periodo_memoria", return_value=True
            ):
                with db.session.no_autoflush:
                    foto = service.snapshot_para_memoria_version(version, 1)[0]
                    self.assertEqual(foto.moneda, "USD")
                    registro.moneda = "ARS"
                    self.assertEqual(foto.moneda, "USD")
                db.session.rollback()

    def test_equipo_usd_no_se_interpreta_como_ars_en_movimientos(self):
        ars = self.equipo()
        usd = self.equipo(moneda="USD")
        disponibles = MovimientoFinancieroService.equipamientos_disponibles(self.grupo.id)
        self.assertEqual([item["id"] for item in disponibles], [ars["id"]])
        with self.assertRaises(ValidationError):
            MovimientoFinancieroService._equipamiento_disponible(usd["id"], self.grupo.id)
        MovimientoFinancieroService.create(self._payload("INGRESO", monto="1000"), 1)
        egreso = MovimientoFinancieroService.create(self._payload(
            "EGRESO", monto="123.45", equipamiento_id=ars["id"], categoria_erogacion_id=self.categoria.id), 1)
        with self.assertRaises(ValidationError):
            EquipamientoService.update(ars["id"], {"moneda": "USD"}, 1)
        db.session.rollback()
        self.assertEqual(db.session.get(MovimientoFinanciero, egreso["id"]).moneda, "ARS")
        self.assertEqual(db.session.get(Equipamiento, ars["id"]).moneda, "ARS")

    def test_dashboard_no_suma_monedas_distintas(self):
        tipo = SimpleNamespace(nombre="Asistencia")
        registros = [SimpleNamespace(tipo_contrato_transferencia=tipo, monto=100, moneda="ARS"),
                     SimpleNamespace(tipo_contrato_transferencia=tipo, monto=50, moneda="USD")]
        fila = DashboardService._transferencias_por_tipo_contrato(registros)[0]
        self.assertEqual((fila["monto_total"], fila["monto_total_usd"], fila["total"]), (100, 50, 2))


class MonedaMigrationTest(unittest.TestCase):
    def test_backfill_constraints_y_reversion_protegida(self):
        path = Path(__file__).resolve().parents[1] / "migrations/versions/f6b8d0e2a4c6_moneda_equipamiento_transferencias.py"
        spec = importlib.util.spec_from_file_location("moneda_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with sa.create_engine("sqlite:///:memory:").begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            for tabla, _ in migration.TABLAS:
                connection.exec_driver_sql(f"CREATE TABLE {tabla} (id INTEGER PRIMARY KEY, monto FLOAT)")
                connection.exec_driver_sql(f"INSERT INTO {tabla} VALUES (1, 123.45)")
            migration.upgrade()
            for tabla, _ in migration.TABLAS:
                self.assertEqual(tuple(connection.exec_driver_sql(f"SELECT monto, moneda FROM {tabla}").one()), (123.45, "ARS"))
                with self.assertRaises(IntegrityError):
                    connection.exec_driver_sql(f"UPDATE {tabla} SET moneda='EUR'")
                connection.exec_driver_sql(f"UPDATE {tabla} SET moneda='USD'")
            with self.assertRaises(RuntimeError):
                migration.downgrade()
            for tabla, _ in migration.TABLAS:
                connection.exec_driver_sql(f"UPDATE {tabla} SET moneda='ARS'")
            migration.downgrade()
            for tabla, _ in migration.TABLAS:
                self.assertEqual(connection.exec_driver_sql(f"SELECT monto FROM {tabla}").scalar_one(), 123.45)
