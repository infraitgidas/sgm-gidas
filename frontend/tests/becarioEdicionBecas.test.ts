import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

test("edición de becario precarga becas, conserva vínculos y envía solo cambios reales", async () => {
  const globals = globalThis as typeof globalThis & { __becasHarness?: any; __becasJsx?: any };
  const h = { cursor: 0, values: [] as any[], deps: [] as any[], effects: [] as Array<() => void>,
    calls: [] as any[], navigations: [] as any[], errors: [] as any[] };
  globals.__becasHarness = h;
  globals.__becasJsx = (type: any, props: any, ...children: any[]) => ({ type, props: props ?? {}, children });
  const url = (source: string) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  const mocks = url(`const h = globalThis.__becasHarness;
    export const useState = initial => { const i = h.cursor++; if (!(i in h.values)) h.values[i] = initial;
      return [h.values[i], next => h.values[i] = typeof next === 'function' ? next(h.values[i]) : next]; };
    export const useEffect = (effect, deps) => { const i = h.cursor++;
      if (!h.deps[i] || deps.some((value, j) => value !== h.deps[i][j])) { h.deps[i] = deps; h.effects.push(effect); } };
    export const useNavigate = () => (...args) => h.navigations.push(args);
    export const useQueryClient = () => ({invalidateQueries: async () => {}});
    export const useAuth = () => ({user: {id: 1}});
    export const useUct = () => ({uct: {id: 1}});
    export const useTiposFormacion = () => ({data: [{id: 1, nombre: 'Grado'}]});
    export const useBecas = () => ({data: [{id: 7, nombre_beca: 'Beca de formación'}, {id: 8, nombre_beca: 'Beca doctoral'}]});
    export const useFormDraft = () => ({availableDraft: null, clearDraft() {}, blocker: {state: 'unblocked'}});
    export const toCivilDateString = date => date ? [date.getFullYear(), String(date.getMonth()+1).padStart(2,'0'), String(date.getDate()).padStart(2,'0')].join('-') : '';
    export const actualizarBecario = async (id, payload) => {h.calls.push({id, payload}); return {id};};
    export const crearBecario = async () => {throw new Error('No debe crear un becario');};
    export const LoaderCircle = () => {}; export default function Component() {}`);
  let js = ts.transpileModule(readFileSync("src/modules/personal/pages/FormBecario.tsx", "utf8"), {
    compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
      jsx: ts.JsxEmit.React, jsxFactory: "globalThis.__becasJsx", jsxFragmentFactory: "String"},
  }).outputText;
  js = js.replace(/from "([^"]+)"/g, (_match, path: string) => `from ${JSON.stringify(
    path === "@/lib/httpError" || path.startsWith("@/modules/personal/utils/")
      ? new URL(`../src/${path.slice(2)}.ts`, import.meta.url).href : mocks)}`);
  const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
    : typeof node === "object" && "children" in node ? [node, ...node.children.flatMap(walk)] : [];
  try {
    const {default: Form} = await import(url(js));
    const base = {id: 3, rol: "becario", nombre: "Ana", apellido: "Pérez", nombre_apellido: "Ana Pérez",
      dni: "12345678", cuil: "20-12345678-6", horas_semanales: 20, tipo_formacion_id: 1,
      fecha_alta_grupo: "2026-01-01", grupo_utn_id: 1, activo: true};
    let initialData: any = {...base, becas: [
      {id: 7, nombre_beca: "Beca de formación", fecha_inicio: "2026-02-01", fecha_fin: "2027-02-01", monto_percibido: 0},
      {id: 8, nombre_beca: "Beca doctoral", fecha_inicio: "2026-03-01", fecha_fin: "2027-03-01", monto_percibido: null},
    ]};
    const render = () => {
      h.cursor = 0;
      const tree = Form({initialData, onCancel() {}, onError: (error: unknown) => h.errors.push(error)});
      const effects = h.effects.splice(0); effects.forEach(effect => effect());
      return tree;
    };
    const nodes = () => walk(render());
    const checkbox = () => nodes().find(n => n.props.id === "checkbox-agregar-beca");
    render();
    assert.equal(checkbox().props.checked, true);
    assert.deepEqual(nodes().filter(n => n.type === "select" && [7, 8].includes(n.props.value)).map(n => n.props.value), [7, 8]);
    const dates = nodes().filter(n => n.props.value instanceof Date).map(n => n.props.value);
    assert.ok(dates.some(d => d.getFullYear() === 2026 && d.getMonth() === 1 && d.getDate() === 1));
    assert.ok(dates.some(d => d.getFullYear() === 2027 && d.getMonth() === 1 && d.getDate() === 1));
    assert.ok(nodes().some(n => n.type === "input" && n.props.type === "number" && n.props.value === 0));
    await render().props.onSubmit({preventDefault() {}});
    assert.equal(h.calls.length, 0, "guardar sin cambios no llama al backend");
    nodes().find(n => n.props["aria-label"] === "Horas semanales").props.onChange({target: {value: "21"}});
    await render().props.onSubmit({preventDefault() {}});
    assert.deepEqual(h.calls, [{id: 3, payload: {horas_semanales: 21}}]);
    assert.equal(h.navigations.at(-1)[0], "/personal/becario/3");
    assert.equal(h.navigations.at(-1)[1].state.successMessage, "¡Actualizado con éxito!");
    checkbox().props.onChange({target: {checked: false}});
    assert.equal(h.calls.length, 1, "desmarcar no persiste hasta guardar");
    await render().props.onSubmit({preventDefault() {}});
    assert.deepEqual(h.calls.at(-1).payload.becas, []);
    initialData = {...base, id: 4, becas: []};
    render();
    assert.equal(checkbox().props.checked, false);
    assert.ok(!nodes().some(n => n.props.id === "becas-search"));
    await render().props.onSubmit({preventDefault() {}});
    assert.equal(h.calls.length, 2, "un becario sin beca tampoco genera diferencias falsas");
    assert.deepEqual(h.errors, []);
  } finally {
    delete globals.__becasHarness;
    delete globals.__becasJsx;
  }
});
