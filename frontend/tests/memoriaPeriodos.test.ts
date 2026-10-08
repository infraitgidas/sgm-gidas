import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
function harness(file: string) {
  const values: any[] = [];
  let cursor = 0;
  const calls: any[] = [];
  const module = { exports: {} as any };
  const code = ts.transpileModule(readFileSync(file, "utf8"), { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
    if (name === "react") return { useState(initial: unknown) {
      const index = cursor++;
      if (!(index in values)) values[index] = initial;
      return [values[index], (next: any) => { values[index] = typeof next === "function" ? next(values[index]) : next; }];
    } };
    if (name === "@tanstack/react-query") return {
      useQuery: () => ({ data: [] }),
      useQueryClient: () => ({ invalidateQueries: async () => {} }),
      useMutation: (options: any) => ({ isPending: false, mutateAsync: async (payload: unknown) => {
        calls.push(payload); await options.onSuccess();
      } }),
    };
    if (name === "@/components/Button") return { default: "button" };
    if (name === "@/components/Field") return { default: "label" };
    if (name === "@/components/Calendar") return { default: "input" };
    if (name === "@/lib/httpError") return { applyFieldErrors: () => false, focusFieldErrors: () => {}, getErrorMessage: (_error: unknown, fallback: string) => fallback };
    if (name === "@/modules/grupo/services/gruposUtnServices") return { getGruposUtn: async () => [] };
    if (name === "@/modules/memorias/services/memoriasService") return { updateMemoria: async () => {} };
    if (name === "@/utils/dateTime") return {
      toCivilDateString: (date: Date | null) => date?.toISOString().slice(0, 10) ?? null,
      formatFecha: (date: string) => date, formatFechaHora: (date: string) => date,
    };
    return require(name);
  } });
  return { calls, render(props: any) { cursor = 0; return module.exports.default(props); } };
}
const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
  : typeof node === "object" && node.props ? [node, ...walk(node.props.children)] : [];

test("GESTOR puede cambiar el estado y el historial identifica la UCT por nombre", () => {
  const source = readFileSync(
    "src/modules/memorias/pages/MemoriaDetalle.tsx",
    "utf8",
  );
  assert.match(source, /const puedeEditar = isAdmin\(\) \|\| isGestor\(\)/);
  assert.match(source, /item\.campo === "grupo_utn_id" \? "UCT"/);
  assert.match(source, /queryKey: \["memoria-historial", id\]/);
  assert.match(source, /"Cerrar memoria"/);
  const routerSource = readFileSync("src/main.tsx", "utf8");
  assert.match(
    routerSource,
    /path: "memorias\/nueva",\s*element: editorOnly\(<MemoriaForm \/>\)/,
  );
});

test("Corrección de memoria no llama al backend sin diferencias y envía solo el fin modificado", async () => {
  const view = harness("src/modules/memorias/components/MemoriaPeriodoForm.tsx");
  let cancel = 0, saved = 0;
  const props = { memoria: { id: 1, grupo_utn_id: 2, periodo_inicio: "2025-07-01", periodo_fin: "2026-06-30" },
    onCancel: () => { cancel++; }, onSaved: () => { saved++; } };
  await view.render(props).props.onSubmit({ preventDefault() {} });
  assert.equal(view.calls.length, 0);
  assert.equal(cancel, 1);
  const dates = walk(view.render(props)).filter(node => node.type === "input");
  dates[1].props.onChange(new Date("2027-06-30T00:00:00Z"));
  await view.render(props).props.onSubmit({ preventDefault() {} });
  assert.equal(JSON.stringify(view.calls), '[{"periodo_fin":"2027-06-30"}]');
  assert.equal(saved, 1);
});

test("Corrección rechaza un rango invertido antes de persistir", async () => {
  const view = harness("src/modules/memorias/components/MemoriaPeriodoForm.tsx");
  const props = { memoria: { id: 1, grupo_utn_id: 2, periodo_inicio: "2025-07-01", periodo_fin: "2026-06-30" },
    onCancel() {}, onSaved() {} };
  walk(view.render(props)).filter(node => node.type === "input")[1].props.onChange(new Date("2025-06-30T00:00:00Z"));
  await view.render(props).props.onSubmit({ preventDefault() {} });
  assert.equal(view.calls.length, 0);
  assert.ok(walk(view.render(props)).some(node => node.props.error === "El fin no puede ser anterior al inicio."));
});

test("Elementos de memoria conserva el acceso anterior al módulo filtrado", () => {
  const source = readFileSync("src/modules/memorias/pages/MemoriaVersionDetalle.tsx", "utf8");
  assert.match(source, /Ver registros en el módulo/);
  assert.match(source, /memoriaFilter:/);
  assert.doesNotMatch(source, /MemoriaSnapshotRecords|Ver datos históricos|Ocultar datos históricos/);
});
