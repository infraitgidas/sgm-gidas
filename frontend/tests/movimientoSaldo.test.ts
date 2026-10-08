import assert from "node:assert/strict";
import test from "node:test";
import { equivalenteArs, excedeSaldoDisponible } from "../src/modules/recursos/utils/movimientoSaldo.ts";

test("un egreso igual al saldo disponible puede guardarse y uno superior no", () => {
  assert.equal(excedeSaldoDisponible("91.00", "91.00"), false);
  assert.equal(excedeSaldoDisponible("91.01", "91.00"), true);
  assert.equal(excedeSaldoDisponible("0.01", "0.00"), true);
});

test("al editar un egreso se reintegra su monto anterior antes de comparar", () => {
  assert.equal(excedeSaldoDisponible("250.00", "200.00", "50.00"), false);
  assert.equal(excedeSaldoDisponible("250.01", "200.00", "50.00"), true);
  assert.equal(excedeSaldoDisponible("40.00", "0.00", "50.00"), false);
});

test("compara centavos exactos aun con importes grandes", () => {
  assert.equal(excedeSaldoDisponible("9999999999999999.01", "9999999999999999.00"), true);
});

test("convierte USD a ARS con redondeo decimal exacto", () => {
  assert.equal(equivalenteArs("1000.00", "1538.390000"), "1538390.00");
  assert.equal(equivalenteArs("0.01", "1.500000"), "0.02");
  assert.equal(equivalenteArs("1000000000000000.00", "1538.390000"), "1538390000000000000.00");
});
