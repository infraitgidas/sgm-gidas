import assert from "node:assert/strict";
import test from "node:test";
import { formatPersonalHistoryEntry } from "../src/modules/personal/utils/personalHistory.ts";

test("presenta la vinculacion de una beca sin exponer el JSON de auditoria", () => {
  const result = formatPersonalHistoryEntry({
    id: 1,
    campo: "becas",
    valor_anterior: null,
    valor_nuevo: {
      accion: "vincular",
      detalle: { beca_id: 5, fecha_inicio: "2023-02-01", fecha_fin: null, monto_percibido: 70000 },
    },
  });

  assert.equal(result.title, "Beca vinculada");
  assert.match(result.description, /Beca #5/);
  assert.match(result.description, /Inicio: 01\/02\/2023/);
  assert.match(result.description, /Sin fecha de fin/);
  assert.match(result.description, /Monto: ARS 70\.000/);
  assert.doesNotMatch(result.description, /accion|detalle|\{|\}/);
});

test("presenta actualizacion, desvinculacion y cambios de campo", () => {
  assert.equal(formatPersonalHistoryEntry({ id: 2, campo: "becas", valor_nuevo: { accion: "desvincular", detalle: { beca_id: 7 } } }).title, "Beca desvinculada");
  assert.equal(formatPersonalHistoryEntry({ id: 3, campo: "becas", valor_nuevo: { accion: "actualizar", detalle: { beca_id: 7 } } }).title, "Beca actualizada");
  assert.deepEqual(formatPersonalHistoryEntry({ id: 4, campo: "horas_semanales", valor_anterior: 10, valor_nuevo: 20 }), {
    title: "Horas semanales",
    description: "10 → 20",
  });
});
