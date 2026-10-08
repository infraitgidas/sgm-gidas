import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  PROYECTO_CODIGO_MAX_LENGTH,
  validateCodigoProyecto,
} from "../src/modules/proyectos/utils/proyectoValidation.ts";

const proyectosFormSource = readFileSync(
  new URL("../src/modules/proyectos/pages/ProyectosForm.tsx", import.meta.url),
  "utf8"
);

test("acepta códigos de proyecto alfanuméricos y conserva su capitalización", () => {
  assert.equal(validateCodigoProyecto("LPSIEC1347"), null);
  assert.equal(validateCodigoProyecto("lpsiec1347"), null);
});

test("acepta códigos numéricos existentes", () => {
  assert.equal(validateCodigoProyecto("3223"), null);
});

test("admite espacios exteriores que el formulario elimina al guardar", () => {
  assert.equal(validateCodigoProyecto("  LPSIEC1347  "), null);
});

test("rechaza un código vacío", () => {
  assert.equal(
    validateCodigoProyecto("   "),
    "Debe ingresar el código del proyecto"
  );
});

test("rechaza caracteres que no son letras o números ASCII", () => {
  assert.equal(
    validateCodigoProyecto("LPSIEC-1347"),
    "El código solo puede contener letras y números"
  );
});

test("rechaza códigos que superan la longitud máxima", () => {
  assert.equal(PROYECTO_CODIGO_MAX_LENGTH, 50);
  assert.equal(
    validateCodigoProyecto("A".repeat(PROYECTO_CODIGO_MAX_LENGTH + 1)),
    "El código no puede superar los 50 caracteres"
  );
});

test("el formulario conserva el código como texto y ofrece feedback accesible", () => {
  assert.match(proyectosFormSource, /codigoProyecto: codigoProyecto\.trim\(\)/);
  assert.doesNotMatch(proyectosFormSource, /codigoProyecto: Number\(/);
  assert.match(proyectosFormSource, /maxLength=\{PROYECTO_CODIGO_MAX_LENGTH\}/);
  assert.match(proyectosFormSource, /aria-invalid=\{Boolean\(errors\.codigoProyecto\)\}/);
  assert.match(proyectosFormSource, /id="codigo-proyecto-error"[\s\S]{0,80}role="alert"/);
});
