import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import ts from "typescript";
import {QueryClient, QueryObserver} from "@tanstack/react-query";

test("formularios Personal, Investigador y Becario enfocan errores y muestran guardado real", async () => {
  const previousDocument = globalThis.document;
  const previousFrame = globalThis.requestAnimationFrame;
  let focused = 0;
  globalThis.document = {querySelectorAll: () => [{dataset: {errorField: "nombre"}, querySelector: () => ({focus: () => focused++})}]} as unknown as Document;
  globalThis.requestAnimationFrame = callback => {callback(0); return 0;};
  const globals = globalThis as typeof globalThis & {__guardarHarness?: any; __guardarJsx?: (...args: any[]) => any};
  globals.__guardarJsx = (type, props, ...children) => ({type, props: props ?? {}, children});
  const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
    : typeof node === "object" && "children" in node ? [node, ...node.children.flatMap(walk)] : [];
  const url = (source: string) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  const mockUrl = url(`const h = globalThis.__guardarHarness;
    export const useState = initial => {const i = h.cursor++; if (!(i in h.values)) h.values[i] = initial; return [h.values[i], next => h.values[i] = typeof next === 'function' ? next(h.values[i]) : next];};
    export const useEffect = () => {}; export const LoaderCircle = () => {};
    export const useNavigate = () => (...args) => h.navigations.push(args);
    export const useQueryClient = () => h.queryClient;
    export const useAuth = () => ({user: {id: 1}});
    export const useFormDraft = options => {h.autosaveModes.push(options.autosave); return {availableDraft: null, clearDraft() {h.clearDrafts++;}, saveStatus: 'idle', blocker: {state: 'unblocked'}, requestLeave: action => h.leaveActions.push(action)};};
    export const toCivilDateString = date => date ? date.toISOString().slice(0, 10) : '';
    export const useUct = () => ({uct: {id: 1}});
    export const useTiposPersonal = () => ({data: [{id: 1, nombre: 'Personal'}]});
    export const useDedicaciones = () => ({data: []});
    export const useCategoriasUtn = () => ({data: []});
    export const useProgramasIncentivos = () => ({data: []});
    export const useTiposFormacion = () => ({data: []}); export const useBecas = () => ({data: []});
    const save = async payload => {h.calls.push(payload); await new Promise((resolve, reject) => {h.resolve = resolve; h.reject = reject;}); h.serverRecords.push({id: 2, nombre_apellido: payload.nombre_apellido}); return {id: 2};};
    export const upsertPersonal = save; export const actualizarPersonal = save;
    export const crearInvestigador = save; export const actualizarInvestigador = save;
    export const crearBecario = save; export const actualizarBecario = save;
    export default function Component() {}`);
  try {
    for (const config of [
      {name: "FormPTAAProfesional", values: ["Persona", "12345678", "20-12345678-6", 20, 1, new Date(2026, 0, 1), true, {}, false], initialData: {id: 1, nombre_apellido: "Persona", dni: "12345678", cuil: "20-12345678-6", horas_semanales: 20, tipo_personal_id: 1, fecha_alta_grupo: "2026-01-01", activo: true}},
      {name: "FormInvestigador", values: ["Persona", "12345678", "20-12345678-6", 20, 1, 1, 1, new Date(2026, 0, 1), true, {}, false], initialData: {id: 1, nombre_apellido: "Persona", dni: "12345678", cuil: "20-12345678-6", horas_semanales: 20, tipo_dedicacion_id: 1, categoria_utn_id: 1, programa_incentivos_id: 1, fecha_alta_grupo: "2026-01-01", activo: true}},
      {name: "FormBecario", values: ["Persona", "12345678", "20-12345678-6", 20, 1, new Date(2026, 0, 1), true, {}, false, [], false], initialData: {id: 1, nombre_apellido: "Persona", dni: "12345678", cuil: "20-12345678-6", horas_semanales: 20, tipo_formacion_id: 1, fecha_alta_grupo: "2026-01-01", activo: true, becas: []}},
    ]) {
      const queryClient = new QueryClient({defaultOptions: {queries: {staleTime: 60_000, retry: false}}});
      const key = ["personal", undefined, "true"];
      const h = {cursor: 0, values: [] as any[], calls: [] as any[], navigations: [] as any[], leaveActions: [] as Array<() => void>, autosaveModes: [] as boolean[], cancels: 0, clearDrafts: 0,
        errors: [] as any[], queryClient, serverRecords: [{id: 1, nombre_apellido: "Anterior"}], resolve: () => {}, reject: (_error: unknown) => {}};
      globals.__guardarHarness = h;
      queryClient.setQueryData(key, [...h.serverRecords]);
      const observer = new QueryObserver(queryClient, {queryKey: key, queryFn: async () => [...h.serverRecords]});
      const unsubscribe = observer.subscribe(() => {});
      let js = ts.transpileModule(readFileSync(`src/modules/personal/pages/${config.name}.tsx`, "utf8"), {compilerOptions: {
        target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
        jsx: ts.JsxEmit.React, jsxFactory: "globalThis.__guardarJsx", jsxFragmentFactory: "String",
      }}).outputText;
      js = js.replace(/from "([^"]+)"/g, (_match, path: string) => {
        const target = path === "../../../lib/textValidation"
          ? new URL("../src/lib/textValidation.ts", import.meta.url).href
          : path === "@/lib/httpError" || path.startsWith("@/modules/personal/utils/")
            ? new URL(`../src/${path.slice(2)}.ts`, import.meta.url).href : `${mockUrl}#${config.name}`;
        return `from ${JSON.stringify(target)}`;
      });
      try {
        const {default: Form} = await import(url(js));
        const render = (initialData?: Record<string, unknown>) => {h.cursor = 0; return Form({initialData, onCancel() {h.cancels++;}, onError: (error: unknown) => h.errors.push(error)});};
        h.values = [...config.values];
        const unchangedBack = walk(render(config.initialData)).find(n => n.props.onClick && n.children.includes("Volver"));
        unchangedBack.props.onClick();
        assert.equal(h.cancels, 1, `${config.name}: vuelve directamente si no hay cambios`);
        assert.equal(h.leaveActions.length, 0, `${config.name}: no abre el diálogo sin cambios`);
        assert.equal(h.clearDrafts, 1, `${config.name}: desactiva el bloqueo antes de volver`);

        h.values = [...config.values];
        h.values[0] = "Persona modificada";
        h.cancels = 0;
        h.clearDrafts = 0;
        const changedBack = walk(render(config.initialData)).find(n => n.props.onClick && n.children.includes("Volver"));
        changedBack.props.onClick();
        assert.equal(h.cancels, 0, `${config.name}: no abandona una edición modificada`);
        assert.equal(h.leaveActions.length, 1, `${config.name}: pide una decisión si hay cambios`);

        h.values = [];
        h.cancels = 0;
        h.clearDrafts = 0;
        h.leaveActions = [];
        const back = walk(render()).find(n => n.props.onClick && n.children.includes("Volver"));
        back.props.onClick();
        assert.equal(h.cancels, 0, `${config.name}: Volver espera la decisión`);
        assert.equal(h.leaveActions.length, 1);
        h.leaveActions[0]();
        assert.equal(h.cancels, 1);
        assert.ok(h.autosaveModes.every(mode => mode === false), `${config.name}: no guarda sin elección`);
        await render().props.onSubmit({preventDefault() {}});
        assert.equal(h.calls.length, 0, config.name);
        assert.match(h.errors[0].message, /Complete o corrija/);
        h.values = [...config.values];
        const pending = render().props.onSubmit({preventDefault() {}});
        const busy = walk(render()).find(n => n.props.type === "submit");
        assert.equal(busy.props.disabled, true, config.name);
        assert.equal(busy.props["aria-busy"], true);
        assert.ok(busy.children.includes("Guardando..."));
        await render().props.onSubmit({preventDefault() {}});
        assert.equal(h.calls.length, 1, "no duplica el envío");
        h.resolve(); await pending;
        assert.equal(h.navigations[0][0], "/personal");
        assert.equal(walk(render()).find(n => n.props.type === "submit").props.disabled, false);
        assert.deepEqual(queryClient.getQueryData(key), h.serverRecords, `${config.name}: refresca el listado activo pese a staleTime`);

        const failure = render().props.onSubmit({preventDefault() {}});
        h.reject(new Error("Servidor no disponible")); await failure;
        assert.equal(h.navigations.length, 1, "no navega después del error");
        assert.equal(h.errors.length, 2);
        assert.equal(walk(render()).find(n => n.props.type === "submit").props.disabled, false);
      } finally {
        unsubscribe(); queryClient.clear();
      }
    }
    assert.equal(focused, 3);
  } finally {
    globalThis.document = previousDocument; globalThis.requestAnimationFrame = previousFrame;
    delete globals.__guardarHarness; delete globals.__guardarJsx;
  }
});
