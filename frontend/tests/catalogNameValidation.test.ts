import assert from "node:assert/strict";
import test from "node:test";
import { hasDescriptiveCatalogName } from "../src/modules/catalogos/utils/catalogNameValidation.ts";

test("catalog names require a Unicode letter and may contain numbers or punctuation", () => {
  for (const value of ["Tipo 2", "Categoría A-1", "Técnico/Administrativo"]) {
    assert.equal(hasDescriptiveCatalogName(value), true);
  }
  for (const value of ["", "  ", "2026", "# ! / 42"]) {
    assert.equal(hasDescriptiveCatalogName(value), false);
  }
});
