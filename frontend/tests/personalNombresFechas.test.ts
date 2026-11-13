import assert from "node:assert/strict";
import test from "node:test";
import { validatePersonalName, validatePersonalStartDate } from "../src/modules/personal/utils/personalValidation.ts";
import { formatPersonalHistoryEntry } from "../src/modules/personal/utils/personalHistory.ts";

test("nombres compuestos, vacios, limites y obligatoriedad de ambos campos", () => {
  assert.deepEqual(validatePersonalName("María del Carmen", "De la Cruz"), {});
  assert.ok(validatePersonalName("Ana", "").apellido);
  assert.ok(validatePersonalName("", "Pérez").nombre);
  assert.ok(validatePersonalName("Ana 1", "Pérez").nombre);
  assert.ok(validatePersonalName("A".repeat(61), "Pérez").nombre);
  assert.ok(validatePersonalName("Texto previo", "").apellido);
});

test("fecha de alta entre 2010 y hoy inclusive", () => {
  const today = new Date(2026, 10, 4);
  for (const valid of [new Date(2010, 0, 1), today]) assert.equal(validatePersonalStartDate(valid, today), null);
  for (const invalid of [null, new Date(NaN), new Date(2009, 11, 31), new Date(2026, 10, 5), new Date(9999, 11, 31)])
    assert.ok(validatePersonalStartDate(invalid, today));
});

test("historial usa etiquetas del servidor y tolera referencias eliminadas", () => {
  for (const campo of ["tipo_personal_id", "tipo_dedicacion_id", "categoria_utn_id", "programa_incentivos_id"]) {
    const item = { id: 1, campo, valor_anterior: 1, valor_nuevo: 2,
      valor_anterior_nombre: "Anterior", valor_nuevo_nombre: "Nuevo" };
    assert.equal(formatPersonalHistoryEntry(item).description, "Anterior → Nuevo");
    assert.equal(formatPersonalHistoryEntry({ ...item, valor_nuevo_nombre: "Referencia no disponible" }).description, "Anterior → Referencia no disponible");
  }
});
