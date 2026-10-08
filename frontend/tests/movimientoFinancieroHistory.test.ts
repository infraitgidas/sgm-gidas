import assert from "node:assert/strict";
import test from "node:test";

import {
  formatMovimientoHistoryEntry,
  formatMovimientoMoney,
  presentMovimientoHistoryItems,
} from "../src/modules/recursos/utils/movimientoHistory.ts";
import type { Erogacion } from "../src/modules/recursos/services/erogacionesServices.ts";

const movimiento = {
  moneda: "ARS",
  fuente: { id: 3, nombre: "UTN" },
  categoria_erogacion: { id: 2, codigo: "CAPITAL", nombre: "Capital" },
} as Erogacion;

test("formatea importes grandes sin perder centavos ni precisión", () => {
  assert.equal(formatMovimientoMoney("9007199254740991.25"), "ARS 9.007.199.254.740.991,25");
  assert.equal(formatMovimientoMoney("0.01"), "ARS 0,01");
  assert.equal(formatMovimientoMoney("100.50", "USD"), "USD 100,50");
});

test("el historial descarta inicializaciones y cambios sin diferencia", () => {
  const visible = presentMovimientoHistoryItems([
    { id: 1, campo: "accion", valor_anterior: "alta", valor_nuevo: "edición" },
    { id: 2, campo: "monto", valor_anterior: null, valor_nuevo: "10.00" },
    { id: 3, campo: "monto", valor_anterior: "10.00", valor_nuevo: "10.00" },
    { id: 4, campo: "monto", valor_anterior: "10.00", valor_nuevo: "11.00" },
  ]);
  assert.deepEqual(visible.map((item) => item.id), [4]);
});

test("las relaciones muestran nombres o una descripción neutra sin IDs", () => {
  const fuente = formatMovimientoHistoryEntry({
    id: 1, campo: "fuente_financiamiento_id", valor_anterior: 9, valor_nuevo: 3,
  }, movimiento);
  assert.equal(fuente.description, "Anterior: Otra fuente de financiamiento · Nuevo: UTN");
  const otra = formatMovimientoHistoryEntry({
    id: 2, campo: "grupo_utn_id", valor_anterior: 7, valor_nuevo: 8,
  }, movimiento);
  assert.doesNotMatch(otra.description, /\b[78]\b|\[object Object\]/);
});
