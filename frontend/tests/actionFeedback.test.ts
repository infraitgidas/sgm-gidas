import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
function load(file: string, react?: unknown) {
  const module = { exports: {} as any };
  const code = ts.transpileModule(readFileSync(file, "utf8"), { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
    if (name === "react" && react) return react;
    if (name === "@/components/Button") return { default: "button" };
    if (name === "@/lib/httpError") return { getErrorMessage: (_error: unknown, fallback: string) => fallback };
    return require(name);
  } });
  return module.exports.default;
}

test("Button anuncia progreso, bloquea la accion y conserva el estado normal", () => {
  const Button = load("src/components/Button.tsx");
  const normal = renderToStaticMarkup(createElement(Button, {}, "Guardar"));
  assert.match(normal, /Guardar/);
  assert.doesNotMatch(normal, /disabled=""/);
  const pending = renderToStaticMarkup(createElement(Button, {
    loading: true, loadingText: "Guardando...", disabled: false,
  }, "Guardar"));
  assert.match(pending, /disabled=""/);
  assert.match(pending, /aria-busy="true"/);
  assert.match(pending, /role="status"/);
  assert.match(pending, /Guardando\.\.\./);
  assert.match(pending, /aria-hidden="true"/);
  const restored = renderToStaticMarkup(createElement(Button, { loading: false, disabled: true }, "Guardar"));
  assert.match(restored, /disabled=""/); // conserva restricciones ajenas a la carga
});

test("ConfirmDialog bloquea doble confirmacion y cancelacion hasta resolver o fallar", async () => {
  const values: any[] = [];
  let cursor = 0;
  const react = {
    useEffect() {},
    useId() { return "dialog-test-id"; },
    useState(initial: unknown) {
      const index = cursor++;
      if (!(index in values)) values[index] = initial;
      return [values[index], (next: unknown) => { values[index] = next; }];
    },
    useRef(initial: unknown) {
      const index = cursor++;
      return values[index] ?? (values[index] = { current: initial });
    },
  };
  const Dialog = load("src/components/ConfirmDialog.tsx", react);
  let calls = 0, cancellations = 0;
  let resolve!: () => void, reject!: (error: Error) => void;
  const props = { open: true, title: "Eliminar", loadingText: "Eliminando...",
    onCancel: () => { cancellations++; },
    onConfirm: () => { calls++; return new Promise<void>((yes, no) => { resolve = yes; reject = no; }); },
  };
  const render = () => { cursor = 0; return Dialog(props); };
  const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
    : typeof node === "object" && node.props ? [node, ...walk(node.props.children)] : [];
  const controls = (tree: any) => walk(tree).filter(node => node.type === "button");
  const initial = controls(render());
  const operation = initial[1].props.onClick();
  await initial[1].props.onClick(); // incluso antes del siguiente render
  initial[0].props.onClick();
  assert.equal(calls, 1);
  assert.equal(cancellations, 0);
  let pending = controls(render());
  assert.equal(pending[0].props.disabled, true);
  assert.equal(pending[1].props.loading, true);
  assert.equal(pending[1].props.loadingText, "Eliminando...");
  resolve();
  await operation;
  assert.equal(controls(render())[1].props.loading, false);

  const failing = controls(render())[1].props.onClick();
  reject(new Error("Error interno"));
  await failing;
  const failedTree = render();
  assert.equal(controls(failedTree)[1].props.loading, false);
  assert.ok(walk(failedTree).some(node => node.props.role === "alert"));
  controls(failedTree)[0].props.onClick();
  assert.equal(cancellations, 1);
});
