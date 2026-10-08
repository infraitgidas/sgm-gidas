import assert from "node:assert/strict";
import test from "node:test";
import { hasLetter, hasOnlyLettersAndSpaces } from "../src/lib/textValidation.ts";

test("nombres descriptivos: exige letras Unicode y permite números adicionales", () => {
  assert.equal(hasLetter("22"), false);
  assert.equal(hasLetter("22-22"), false);
  assert.equal(hasLetter("..."), false);
  assert.equal(hasLetter("Ana 22"), true);
  assert.equal(hasLetter("Ñandú 2"), true);
});

test("nombres de personas, directivos, autores y adoptantes admiten solo letras y espacios", () => {
  for (const valid of ["Ana", "Ana María", "Ñandú", "  José Luis  "]) {
    assert.equal(hasOnlyLettersAndSpaces(valid), true, valid);
  }
  for (const invalid of ["", "22", "Ana 22", "Ana-María", "Ana!", "Ana_María", "Ana\tMaría"]) {
    assert.equal(hasOnlyLettersAndSpaces(invalid), false, invalid);
  }
  assert.equal(hasLetter("Proyecto 22"), true);
});
