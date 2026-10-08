import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { MAX_HORAS_SEMANALES, validWeeklyHours } from "../src/modules/personal/utils/weeklyHours.ts";

test("horas semanales: enteros entre 1 y las 168 horas reales de la semana", () => {
  assert.equal(MAX_HORAS_SEMANALES, 168);
  for (const hours of [1, 20, 168]) assert.equal(validWeeklyHours(hours), true);
  for (const hours of ["", "20", null, true, 0, -1, 1.5, 169, 220, Infinity, NaN]) {
    assert.equal(validWeeklyHours(hours), false, String(hours));
  }
});

test("Personal, Becario e Investigador validan horas antes de guardar", () => {
  for (const page of ["FormPTAAProfesional", "FormBecario", "FormInvestigador"]) {
    const source = readFileSync(`src/modules/personal/pages/${page}.tsx`, "utf8");
    assert.match(source, /validWeeklyHours\(horasSemanales\)/);
    assert.match(source, /max=\{MAX_HORAS_SEMANALES\}/);
    assert.match(source, /step="1"/);
    assert.match(source, /if \(!validate\(\)\) return/);
  }
});
