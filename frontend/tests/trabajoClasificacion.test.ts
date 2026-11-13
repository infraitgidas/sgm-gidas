import assert from "node:assert/strict";
import test from "node:test";
import { referatoLabel, alcanceLabel, procedenciaLabel, referatoValue } from "../src/modules/produccion/utils/clasificacionTrabajo.ts";
import { formatTrabajoReunionHistoryEntry, isVisibleTrabajoReunionHistoryItem } from "../src/modules/produccion/utils/trabajoReunionHistory.ts";
import { formatTrabajoRevistaHistoryEntry, isVisibleTrabajoRevistaHistoryItem } from "../src/modules/produccion/utils/trabajoRevistaHistory.ts";

test("referato conserva No frente a Sin informar y presenta la geografía requerida", () => {
  assert.equal(referatoValue("false"), false);
  assert.equal(referatoValue("true"), true);
  assert.equal(referatoValue(""), null);
  assert.equal(referatoLabel(false), "No");
  assert.equal(referatoLabel(null), "Sin informar");
  assert.equal(alcanceLabel("internacional"), "Internacional");
  assert.equal(procedenciaLabel("nacional"), "Ciudad");
  assert.equal(procedenciaLabel("internacional"), "País");
  assert.equal(procedenciaLabel(null), "Procedencia");
});

test("clasificar un histórico es un cambio visible; limpiar y cambiar booleanos también", () => {
  for (const visible of [isVisibleTrabajoReunionHistoryItem, isVisibleTrabajoRevistaHistoryItem]) {
    for (const [anterior, nuevo] of [[null, false], [null, true], [true, false], [false, null]]) {
      assert.equal(visible({ id: 1, campo: "referato", valor_anterior: anterior, valor_nuevo: nuevo }), true);
    }
    assert.equal(visible({ id: 1, campo: "referato", valor_anterior: false, valor_nuevo: false }), false);
  }
  const cambio = { id: 1, campo: "referato", valor_anterior: null, valor_nuevo: false };
  for (const format of [formatTrabajoReunionHistoryEntry, formatTrabajoRevistaHistoryEntry]) {
    assert.deepEqual(format(cambio), { title: "Referato", description: "Sin informar → No" });
  }
  assert.equal(isVisibleTrabajoReunionHistoryItem({ id: 1, campo: "alcance", valor_anterior: null, valor_nuevo: "nacional" }), true);
  assert.deepEqual(formatTrabajoReunionHistoryEntry({ id: 1, campo: "alcance", valor_anterior: "nacional", valor_nuevo: "internacional" }), {
    title: "Alcance", description: "Nacional → Internacional",
  });
});
