import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const uctFormSource = readFileSync(
  new URL("../src/modules/grupo/pages/UctForm.tsx", import.meta.url),
  "utf8"
);
const directivosHookSource = readFileSync(
  new URL("../src/modules/grupo/hooks/useDirectivos.ts", import.meta.url),
  "utf8"
);

test("el formulario consulta el equipo mediante el hook de directivos actuales", () => {
  assert.match(uctFormSource, /useDirectivos\(grupoId, !hasStartedSave\.current\)/);
  assert.match(directivosHookSource, /enabled: enabled && !!grupoId/);
  assert.doesNotMatch(directivosHookSource, /invalidateQueries/);
  assert.doesNotMatch(uctFormSource, /uct\?\.directivos/);
});

test("un guardado exitoso vuelve al inicio con feedback por navegacion", () => {
  assert.match(uctFormSource, /navigate\("\/inicio",\s*\{/);
  assert.match(uctFormSource, /state:\s*\{\s*successMessage:/);
});
