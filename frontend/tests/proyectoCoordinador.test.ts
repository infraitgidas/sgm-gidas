import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

type Element = { type: any; props: Record<string, any>; children: any[] };

test("formulario real guarda coordinador en una petición, conserva edición y muestra estados", async () => {
  const initial = {
    id: "1", nombreProyecto: "Proyecto", codigoProyecto: "ABC1", descripcionProyecto: "Descripción",
    dificultadesProyecto: "", fechaInicio: "2026-01-01", fechaFinalizacion: "2026-12-31", tipoProyectoId: 1, grupoUtnId: 1,
    investigadores: [{ id: 1, nombre_apellido: "Persona A", es_coordinador: true },
      { id: 2, nombre_apellido: "Persona B", es_coordinador: false }],
  };
  const h = {
    values: ["Proyecto", "ABC1", "Descripción", "", "", "", new Date(2026, 0, 1), new Date(2026, 11, 31),
      1, null, [1, 2], 1, [], {}, false, "", true, 1] as any[],
    cursor: 0, id: undefined as string | undefined, initial,
    candidates: [{id: 1, nombre_apellido: "Persona A"}, {id: 2, nombre_apellido: "Persona B"}],
    loading: false, error: false, calls: [] as any[], navigations: [] as any[], pending: Promise.resolve(),
    serverError: undefined as unknown, focused: 0,
  };
  const globals = globalThis as typeof globalThis & {
    __proyectoHarness?: typeof h; __proyectoJsx?: (...args: any[]) => Element;
  };
  globals.__proyectoHarness = h;
  const previousDocument = globalThis.document;
  const previousFrame = globalThis.requestAnimationFrame;
  globalThis.document = {querySelectorAll: () => [{dataset: {errorField: "investigadoresIds"}, querySelector: () => ({focus: () => h.focused++})}]} as unknown as Document;
  globalThis.requestAnimationFrame = callback => {callback(0); return 0;};
  globals.__proyectoJsx = (type, props, ...children) => ({type, props: props ?? {}, children});
  const mock = `const h = globalThis.__proyectoHarness;
    export const useState = initial => {const i = h.cursor++; return [h.values[i], next => h.values[i] = typeof next === 'function' ? next(h.values[i]) : next];};
    export const useMemo = fn => fn(); export const useEffect = () => {};
    export const LoaderCircle = () => {};
    export const useParams = () => ({id: h.id});
    export const useNavigate = () => (...args) => h.navigations.push(args);
    export const useQueryClient = () => ({invalidateQueries: async () => {}});
    export const useQuery = options => options.queryKey[0] === 'proyecto-candidatos'
      ? {data: h.candidates, isLoading: h.loading, isError: h.error, refetch: async () => {}}
      : {data: h.id ? h.initial : undefined, isLoading: false};
    export const useMutation = options => ({isPending: false, mutate: payload => {h.pending = options.mutationFn(payload).then(options.onSuccess, options.onError);}});
    export const useTiposProyecto = () => ({data: [{id: 1, nombre: 'Investigación'}]});
    export const useFuentesFinanciamiento = () => ({fuentes: []});
    export const useBecarios = () => ({data: []});
    export const useUct = () => ({uct: {id: 1}});
    export const useAuth = () => ({user: {id: 7}});
    export const useFormDraft = () => ({clearDraft() {}, restoreDraft() {}, discardDraft() {}, blocker: {state: 'unblocked', reset() {}}, keepAndLeave: async () => true, discardAndLeave: async () => {}});
    export const getInvestigadores = async () => h.candidates;
    export const http = async (path, options) => {h.calls.push({path, options}); if (h.serverError) throw h.serverError; return {id: 1, tipo_proyecto_id: 1, codigo_proyecto: 'ABC1', nombre_proyecto: 'Proyecto', fecha_inicio: '2026-01-01'};};
    export default function Component() {}`;
  const url = (source: string) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  const mockUrl = url(mock);
  const compile = (source: string) => ts.transpileModule(source, {compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    jsx: ts.JsxEmit.React, jsxFactory: "globalThis.__proyectoJsx",
    jsxFragmentFactory: "String",
  }}).outputText;
  const serviceUrl = url(compile(readFileSync("src/modules/proyectos/services/proyectosServices.ts", "utf8"))
    .replace(/from "[^"]+"/g, `from "${mockUrl}"`));
  const js = compile(readFileSync("src/modules/proyectos/pages/ProyectosForm.tsx", "utf8"))
    .replace(/from "([^"]+)"/g, (_match, path: string) => {
      const target = path === "../../../lib/textValidation" ? new URL("../src/lib/textValidation.ts", import.meta.url).href
        : path === "@/modules/proyectos/services/proyectosServices" ? serviceUrl
        : path === "@/lib/httpError" || path === "@/utils/dateTime" || path === "@/modules/proyectos/utils/proyectoValidation"
          ? new URL(`../src/${path.slice(2)}.ts`, import.meta.url).href : mockUrl;
      return `from ${JSON.stringify(target)}`;
    });
  const walk = (node: any): Element[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
    : typeof node === "object" && "children" in node ? [node, ...node.children.flatMap(walk)] : [];
  const text = (node: any): string => !node ? "" : Array.isArray(node) ? node.map(text).join(" ")
    : typeof node === "object" && "children" in node ? text(node.children) : typeof node === "string" ? node : "";
  try {
    const {default: Form} = await import(url(js));
    const render = () => {h.cursor = 0; return Form();};
    const submit = async () => {
      walk(render()).find(n => n.type === "form")!.props.onSubmit({preventDefault() {}});
      await h.pending;
    };
    assert.equal(walk(render()).filter(n => n.type === "input" && n.props.type === "radio").length, 2);
    await submit();
    assert.equal(h.calls.length, 1);
    assert.equal(h.calls[0].path, "/proyectos");
    assert.deepEqual(JSON.parse(h.calls[0].options.body).investigadores_ids, [1, 2]);
    assert.equal(JSON.parse(h.calls[0].options.body).coordinador_id, 1);
    assert.equal(h.navigations[0][0], "/proyectos");

    h.id = "1"; h.calls = []; h.navigations = [];
    h.values[13] = {};
    await submit();
    assert.equal(h.calls.length, 0);
    assert.equal(h.navigations[0][0], "/proyectos/1");

    const logros = walk(render()).find(n => n.type === "textarea" && n.props.maxLength === 20000)!;
    logros.props.onChange({target: {value: "Modelo de simulación validado."}});
    await submit();
    assert.deepEqual(JSON.parse(h.calls[0].options.body), {logros_obtenidos: "Modelo de simulación validado."});
    h.values[3] = ""; h.calls = [];

    const radioB = walk(render()).filter(n => n.type === "input" && n.props.type === "radio")[1];
    radioB.props.onChange();
    await submit();
    assert.equal(h.calls.length, 1);
    assert.deepEqual(JSON.parse(h.calls[0].options.body), {coordinador_id: 2});

    h.calls = []; h.values[10] = [1, 2, 0];
    await submit();
    assert.equal(h.calls.length, 0);
    assert.match(h.values[13].investigadoresIds, /vacías/);
    assert.equal(h.values[14], true);
    assert.match(h.values[15], /Complete o corrija/);
    assert.equal(h.focused, 1);

    h.values[10] = []; h.values[11] = null; h.id = undefined; h.candidates = [];
    assert.match(text(render()), /No hay investigadores activos disponibles/);
    h.loading = true;
    assert.ok(walk(render()).some(node => node.props.label === "Cargando investigadores..."));
    h.loading = false; h.error = true;
    assert.match(text(render()), /Reintentar/);
    await submit();
    assert.equal(h.calls.length, 0);

    h.error = false; h.id = "1"; h.values[10] = [1, 2]; h.values[11] = 1;
    assert.match(text(render()), /inactivo, asignación conservada/);
    const radios = walk(render()).filter(n => n.type === "input" && n.props.type === "radio");
    assert.equal(radios[0].props.checked, true);
    assert.equal(radios[1].props.disabled, true);

    h.candidates = [{id: 1, nombre_apellido: "Persona A"}, {id: 2, nombre_apellido: "Persona B"}];
    h.values[11] = 2;
    h.values[14] = false; h.values[15] = "";
    h.serverError = {body: {error: {message: "Seleccione un investigador disponible.", details: {fields: {coordinador_id: "Coordinador no disponible."}}}}};
    await submit();
    assert.equal(h.values[13].coordinadorId, "Coordinador no disponible.");
    assert.equal(h.values[14], false);
    assert.equal(h.values[15], "");

    h.calls = []; h.serverError = undefined; h.values[7] = new Date(2025, 11, 31);
    await submit();
    assert.equal(h.calls.length, 0);
    assert.match(h.values[13].fechaFin, /12 a 36/);
  } finally {
    globalThis.document = previousDocument;
    globalThis.requestAnimationFrame = previousFrame;
    delete globals.__proyectoHarness; delete globals.__proyectoJsx;
  }
});
