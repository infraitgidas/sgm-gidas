import assert from "node:assert/strict";
import test from "node:test";
import {
  EQUIPAMIENTO_MIN_FECHA_INCORPORACION,
  validateFechaIncorporacion,
} from "../src/modules/recursos/utils/equipamientoValidation.ts";

const today = "2026-09-09";

test("acepta el limite inferior de incorporacion", () => {
  assert.equal(EQUIPAMIENTO_MIN_FECHA_INCORPORACION, "2010-01-01");
  assert.equal(validateFechaIncorporacion("2010-01-01", today), null);
});

test("rechaza fechas anteriores a 2010", () => {
  assert.equal(
    validateFechaIncorporacion("1900-01-01", today),
    "La fecha de incorporación debe ser igual o posterior al 01/01/2010"
  );
});

test("acepta la fecha actual", () => {
  assert.equal(validateFechaIncorporacion(today, today), null);
});

test("rechaza fechas posteriores a la fecha actual", () => {
  assert.equal(
    validateFechaIncorporacion("2026-09-10", today),
    "La fecha de incorporación no puede ser posterior a la fecha actual"
  );
});

test("rechaza fechas inexistentes", () => {
  assert.equal(
    validateFechaIncorporacion("2026-02-31", today),
    "La fecha ingresada no es válida"
  );
});

test("mantiene la fecha como obligatoria", () => {
  assert.equal(validateFechaIncorporacion("", today), "La fecha es obligatoria");
});
