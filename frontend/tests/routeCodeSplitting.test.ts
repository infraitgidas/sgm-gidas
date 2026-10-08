import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const mainSource = await readFile(new URL("../src/main.tsx", import.meta.url), "utf8");

test("carga las paginas mediante imports dinamicos", () => {
  const lazyPages = mainSource.match(/lazy\(\(\) => import\("@\/modules\//g) ?? [];

  assert.ok(lazyPages.length >= 50, `se esperaban al menos 50 paginas diferidas y se encontraron ${lazyPages.length}`);
  assert.doesNotMatch(mainSource, /^import\s+\w+\s+from\s+"@\/modules\/.*\/pages\//m);
});

test("muestra feedback accesible durante la carga y permite recuperar errores", async () => {
  assert.match(mainSource, /<Suspense fallback={<RouteLoading \/>}>/);
  assert.match(mainSource, /<LoadingSkeleton label="Cargando contenido/);
  assert.match(await readFile(new URL("../src/components/LoadingSkeleton.tsx", import.meta.url), "utf8"), /role="status" aria-live="polite"/);
  assert.match(mainSource, /<RouteErrorBoundary>/);
  assert.match(mainSource, /window\.location\.reload\(\)/);
  assert.match(mainSource, />\s*Reintentar\s*</);
});
