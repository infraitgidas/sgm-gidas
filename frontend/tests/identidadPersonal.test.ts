import assert from "node:assert/strict";
import test from "node:test";
import { validateCuil, validateDni } from "../src/modules/personal/utils/identidadValidation.ts";

test("DNI acepta 7 u 8 digitos sin separadores", () => {
  assert.equal(validateDni("12345678"), null);
  assert.equal(validateDni("1234567"), null);
  for (const value of ["", "123456", "12.345.678", "123456789", "12345ABC"]) {
    assert.notEqual(validateDni(value), null);
  }
});

test("CUIL exige formato, DNI coincidente y digito verificador", () => {
  assert.equal(validateCuil("20-12345678-6", "12345678"), null);
  for (const value of ["20123456786", "20-12345678-7", "20-12345679-4"]) {
    assert.notEqual(validateCuil(value, "12345678"), null);
  }
});
