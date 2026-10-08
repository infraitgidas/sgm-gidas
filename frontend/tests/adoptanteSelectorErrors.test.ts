import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const source = readFileSync(new URL("../src/components/AdoptanteSelector.tsx", import.meta.url), "utf8");

test("el alta inline conserva el nombre y muestra el error del servidor junto al campo", async () => {
  const values: unknown[] = [];
  let cursor = 0;
  let focused = 0;
  const module = { exports: {} as { default: (props: unknown) => unknown } };
  const error = { body: { error: { details: { fields: { nombre: "Elija otro nombre o seleccione el adoptante existente" } } } } };
  const code = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.CommonJS,
    jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  const previousDocument = globalThis.document;
  const previousFrame = globalThis.requestAnimationFrame;
  globalThis.document = { querySelectorAll: () => [{ dataset: { errorField: "nombre" }, querySelector: () => ({ focus: () => { focused++; } }) }] } as unknown as Document;
  globalThis.requestAnimationFrame = (callback) => { callback(0); return 0; };
  try {
    runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
      if (name === "react") return {
        useState(initial: unknown) {
          const index = cursor++;
          if (!(index in values)) values[index] = initial;
          return [values[index], (next: unknown) => {
            values[index] = typeof next === "function" ? (next as (value: unknown) => unknown)(values[index]) : next;
          }];
        },
        useMemo: (fn: () => unknown) => fn(),
      };
      if (name === "react/jsx-runtime") return { jsx: (type: unknown, props: unknown) => ({ type, props }), jsxs: (type: unknown, props: unknown) => ({ type, props }) };
      if (name === "@/components/Button") return { default: "button" };
      if (name === "@/components/SuccessToast") return { default: "toast" };
      if (name === "@/modules/transferencia/hooks/useAdoptantes") return {
        useAdoptantes: () => ({ list: [] }),
        useCreateAdoptante: () => ({ isPending: false, mutateAsync: async () => { throw error; } }),
      };
      if (name === "@/lib/httpError") return require("../src/lib/httpError.ts");
      if (name === "../lib/textValidation") return require("../src/lib/textValidation.ts");
      return require(name);
    } });
    const render = () => { cursor = 0; return module.exports.default({ selected: [], onChange() {} }); };
    const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
      : typeof node === "object" && node.props ? [node, ...walk(node.props.children)] : [];
    walk(render()).find(node => node.type === "button" && node.props.children === "+ Crear nuevo adoptante")!.props.onClick();
    const input = () => walk(render()).find(node => node.type === "input" && node.props.id === "nuevo-adoptante-nombre")!;
    input().props.onChange({ target: { value: "Ada" } });
    await walk(render()).find(node => node.type === "button" && node.props.children === "Crear y agregar")!.props.onClick();
    assert.equal(input().props.value, "Ada");
    assert.equal(input().props["aria-invalid"], true);
    assert.ok(walk(render()).some(node => node.props.role === "alert" && node.props.children.includes("Elija otro nombre")));
    assert.equal(focused, 1);
    assert.equal(walk(render()).find(node => node.type === "toast")!.props.open, false);
  } finally {
    globalThis.document = previousDocument;
    globalThis.requestAnimationFrame = previousFrame;
  }
});
