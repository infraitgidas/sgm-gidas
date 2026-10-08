import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

type Element = { type: string; props: Record<string, any>; children: any[] };

test("formulario real muestra catálogo arbitrario, envía su ID y bloquea 220 horas", async () => {
  const harness = {
    values: ["Persona", "12345678", "20-12345678-6", 20, 37, new Date(2026, 8, 1), true, {}] as any[],
    cursor: 0, calls: [] as any[], catalog: [{ id: 37, nombre: "Especialista de laboratorio" }],
    errors: [] as unknown[], focused: 0,
  };
  const globals = globalThis as typeof globalThis & { __personalHarness?: typeof harness; __personalJsx?: (...args: any[]) => Element };
  globals.__personalHarness = harness;
  const previousDocument = globalThis.document;
  const previousFrame = globalThis.requestAnimationFrame;
  globalThis.document = { querySelectorAll: () => [{dataset: {errorField: "horas"}, querySelector: () => ({focus: () => harness.focused++})}] } as unknown as Document;
  globalThis.requestAnimationFrame = callback => { callback(0); return 0; };
  globals.__personalJsx = (type, props, ...children) => ({ type, props: props ?? {}, children });
  const mock = `const h = globalThis.__personalHarness;
    export const useState = initial => { const i = h.cursor++; return [h.values[i] ?? initial, next => h.values[i] = typeof next === 'function' ? next(h.values[i]) : next]; };
    export const useEffect = () => {};
    export const LoaderCircle = () => {};
    export const useNavigate = () => (...args) => h.calls.push({navigate: args});
    export const useUct = () => ({uct: {id: 1}});
    export const useTiposPersonal = () => ({data: h.catalog, isLoading: false, isError: false, refetch: async () => {}});
    export const useQueryClient = () => ({invalidateQueries: async () => {}});
    export const useAuth = () => ({user: {id: 1}});
    export const useFormDraft = () => ({availableDraft: null, clearDraft() {}, saveStatus: 'idle', blocker: {state: 'unblocked'}});
    export const toCivilDateString = date => date ? date.toISOString().slice(0, 10) : '';
    export const upsertPersonal = async payload => { h.calls.push({payload}); return {id: 1}; };
    export const actualizarPersonal = async () => {};
    export default function Component() {}`;
  const mockUrl = `data:text/javascript;base64,${Buffer.from(mock).toString("base64")}`;
  const source = readFileSync("src/modules/personal/pages/FormPTAAProfesional.tsx", "utf8");
  let js = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    jsx: ts.JsxEmit.React, jsxFactory: "globalThis.__personalJsx",
  } }).outputText;
  js = js.replace(/from "([^"]+)"/g, (_match, path: string) => {
    const url = path === "../../../lib/textValidation"
      ? new URL("../src/lib/textValidation.ts", import.meta.url).href
      : path === "@/lib/httpError" || path.startsWith("@/modules/personal/utils/")
        ? new URL(`../src/${path.slice(2)}.ts`, import.meta.url).href : mockUrl;
    return `from ${JSON.stringify(url)}`;
  });
  const walk = (node: any): Element[] => !node ? [] : Array.isArray(node)
    ? node.flatMap(walk) : typeof node === "object" && "children" in node
      ? [node, ...node.children.flatMap(walk)] : [];
  try {
    const { default: Form } = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);
    const render = () => { harness.cursor = 0; return Form({onCancel: () => {}, onError: (e: unknown) => harness.errors.push(e)}); };
    let tree = render();
    const options = walk(tree).filter(node => node.type === "option");
    assert.ok(options.some(node => node.props.value === 37 && node.children.includes("Especialista de laboratorio")));
    assert.equal(options.length, 2); // placeholder y catálogo, sin opciones prefijadas
    await tree.props.onSubmit({preventDefault() {}});
    assert.equal(harness.calls[0].payload.tipo_personal_id, 37);
    assert.equal(harness.calls[0].payload.horas_semanales, 20);
    assert.equal(harness.calls[1].navigate[0], "/personal");
    harness.calls = [];
    harness.values[3] = 220;
    tree = render();
    await tree.props.onSubmit({preventDefault() {}});
    assert.equal(harness.calls.length, 0);
    assert.match(harness.values[7].horas, /168/);
    assert.equal(harness.focused, 1);
    assert.match((harness.errors[0] as Error).message, /Complete o corrija/);
    harness.values[3] = 168;
    tree = render();
    await tree.props.onSubmit({preventDefault() {}});
    assert.equal(harness.calls[0].payload.horas_semanales, 168);
    harness.calls = [];
    harness.catalog = [];
    tree = render();
    assert.ok(walk(tree).some(node => node.type === "select" && node.props.disabled));
    await tree.props.onSubmit({preventDefault() {}});
    assert.equal(harness.calls.length, 0);
    assert.ok(harness.values[7].tipoPersonal);
  } finally {
    globalThis.document = previousDocument;
    globalThis.requestAnimationFrame = previousFrame;
    delete globals.__personalHarness;
    delete globals.__personalJsx;
  }
});
