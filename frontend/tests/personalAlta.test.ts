import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { personalFieldErrors } from "../src/modules/personal/utils/personalFieldErrors.ts";

test("alta PTAA usa la ruta POST canónica sin barra final", () => {
  const source = readFileSync("src/modules/personal/services/personalServices.ts", "utf8");
  assert.match(source, /http<PersonalItem>\("\/personal",\s*\{\s*method: "POST"/);
});

test("errores del contrato se asocian a los campos visibles", () => {
  assert.deepEqual(personalFieldErrors({body: {error: {details: {fields: {
    tipo_personal_id: "Seleccione otro tipo", horas_semanales: "Horas enteras",
    grupo_utn_id: "Revise el grupo", secreto: "No mostrar",
  }}}}}), {tipoPersonal: "Seleccione otro tipo", horas: "Horas enteras", grupo: "Revise el grupo"});
  for (const error of [null, {}, {body: "SQL"}, {body: {error: "Error"}}]) {
    assert.deepEqual(personalFieldErrors(error), {});
  }
});

test("formulario Personal usa catálogo real y feedback", () => {
  const source = readFileSync("src/modules/personal/pages/FormPTAAProfesional.tsx", "utf8");
  assert.match(source, /tiposPersonal\.map/);
  assert.match(source, /tipo_personal_id: Number\(tipoPersonalId\)/);
  assert.doesNotMatch(source, /tipoProfesional|tiposPersonalParaPTAA|includes\("profesional"\)/);
  assert.match(source, /validWeeklyHours\(horasSemanales\)/);
  assert.match(source, /personalFieldErrors\(error\)/);
  assert.match(source, /personal-tipoPersonal/);
  assert.match(source, /navigate\("\/personal",/);
});
