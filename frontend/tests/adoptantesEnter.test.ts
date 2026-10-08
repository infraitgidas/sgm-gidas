import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);

test("Enter en nombre de adoptante lo añade sin enviar el formulario", () => {
  const source = readFileSync("src/modules/transferencia/components/AdoptantesField.tsx", "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const module = { exports: {} as { default: (props: unknown) => unknown } };
  const state: unknown[] = [];
  let cursor = 0;
  let selected: Array<{ id: number; nombre: string }> = [];
  runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
    if (name === "react") return {
      useState(initial: unknown) {
        const index = cursor++;
        if (!(index in state)) state[index] = initial;
        return [state[index], (next: unknown) => { state[index] = typeof next === "function" ? (next as (value: unknown) => unknown)(state[index]) : next; }];
      },
      useMemo: (compute: () => unknown) => compute(),
    };
    if (name === "react/jsx-runtime") return { jsx: (type: unknown, props: unknown) => ({ type, props }), jsxs: (type: unknown, props: unknown) => ({ type, props }) };
    if (name === "@/components/Button") return { default: "button" };
    if (name === "@/components/LoadingSkeleton") return { default: "div" };
    if (name === "@/modules/transferencia/hooks/useAdoptantes") return { useAdoptantes: () => ({ list: [], isLoading: false, isError: false }) };
    if (name === "@/lib/textValidation") return require("../src/lib/textValidation.ts");
    return require(name);
  } });
  const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk) : typeof node === "object" && node.props ? [node, ...walk(node.props.children)] : [];
  const render = () => { cursor = 0; return walk(module.exports.default({ selected, onChange: (items: typeof selected) => { selected = items; } })); };

  render().find(node => node.type === "button" && node.props.children === "Nuevo adoptante")!.props.onClick();
  let input = render().find(node => node.type === "input" && node.props.id === "adoptante-nombre")!;
  input.props.onChange({ target: { value: "Instituto Regional" } });
  input = render().find(node => node.type === "input" && node.props.id === "adoptante-nombre")!;
  let prevented = false;
  input.props.onKeyDown({ key: "Enter", nativeEvent: { isComposing: false }, preventDefault: () => { prevented = true; } });
  assert.equal(prevented, true);
  assert.deepEqual(Array.from(selected, item => item.nombre), ["Instituto Regional"]);
  assert.ok(selected[0].id < 0);
  assert.equal(render().some(node => node.props.children === "El adoptante se creará al guardar la transferencia."), false);
});
