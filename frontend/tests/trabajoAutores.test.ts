import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
function load(file: string, mocks: Record<string, unknown> = {}) {
  const module = { exports: {} as any };
  const code = ts.transpileModule(readFileSync(file, "utf8"), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  runInNewContext(code, { URL, module, exports: module.exports, require: (name: string) => {
    if (name in mocks) return mocks[name];
    if (name === "@/utils/dateTime") return { toCivilDateString: (date: Date | null) => date ? date.toISOString().slice(0, 10) : "" };
    if (name === "@/modules/shared/hooks/useFormDraft") return { useFormDraft: () => ({ availableDraft: null, clearDraft() {}, saveStatus: "idle", blocker: { state: "unblocked" } }) };
    if (name.startsWith("@/components/") || name.startsWith("@/modules/produccion/components/")) return { default: name.split("/").at(-1) };
    if (name === "@/modules/produccion/utils/trabajoEnlace") return load("src/modules/produccion/utils/trabajoEnlace.ts");
    if (name === "../../../lib/textValidation") return require("../src/lib/textValidation.ts");
    if (name.startsWith("@/")) return {};
    return require(name);
  } });
  return module.exports;
}
const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
  : typeof node === "object" && node.props ? [node, ...walk(node.props.children)] : [];
const contratos = load("src/modules/produccion/services/trabajoAutoresServices.ts");
const investigador = { id: 1, rol: "investigador", tipo: "Investigador", nombre_apellido: "Ana", activo: true };
const becario = { id: 1, rol: "becario", tipo: "Becario", nombre_apellido: "Luis", activo: true };

test("El service de autores excluye al resto del personal del listado combinado", async () => {
  const service = load("src/modules/produccion/services/trabajoAutoresServices.ts", {
    "@/lib/http": { http: async () => [investigador, becario,
      { id: 1, rol: "personal", nombre_apellido: "Eva", tipo_personal: "Profesional", activo: true },
      { id: 2, rol: "externo", nombre_apellido: "Otra categoría", activo: true },
      { ...becario, id: 3, activo: false }],
    },
  });
  const autores = await service.getIntegrantesAutores();
  assert.equal(autores.length, 2);
  assert.equal(JSON.stringify(autores.map((autor: any) => autor.rol)), '["investigador","becario"]');
  assert.equal(JSON.stringify(autores.map((autor: any) => autor.tipo)), '["Investigador","Becario"]');
});

function selectorHarness(initialValue: any[], options: any[]) {
  let value = initialValue, cursor = 0;
  const states: any[] = [];
  const Field = load("src/modules/produccion/components/IntegrantesAutoresField.tsx", {
    react: { useId: () => "autores", useState(initial: unknown) {
      const index = cursor++;
      if (!(index in states)) states[index] = initial;
      return [states[index], (next: any) => { states[index] = typeof next === "function" ? next(states[index]) : next; }];
    } },
    "@/modules/produccion/services/trabajoAutoresServices": contratos,
  }).default;
  const render = (disabled = false) => { cursor = 0; return walk(Field({ value, options, disabled, onChange: (next: any) => { value = next; } })); };
  return { render, value: () => value };
}

test("El buscador añade solo por botón, excluye personal e inactivos y conserva bajas locales", () => {
  const h = selectorHarness([{ ...investigador, activo: false }], [becario,
    { id: 1, rol: "personal", tipo: "PTAA", nombre_apellido: "Eva", activo: true },
    { ...becario, id: 3, activo: false }]);
  const nodes = h.render();
  assert.match(JSON.stringify(nodes.map(node => node.props.children)), /Inactivo/);
  const buttons = () => h.render().filter(node => node.type === "Button");
  assert.equal(buttons().filter(node => node.props.children === "Añadir").length, 1);
  const search = nodes.find(node => node.type === "input");
  search.props.onChange({ target: { value: "L" } });
  assert.equal(h.value().length, 1);
  assert.equal(search.props.onBlur, undefined);
  let prevented = false;
  search.props.onKeyDown({ key: "Enter", preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(h.value().length, 1);
  buttons().find(node => node.props.children === "Añadir").props.onClick();
  assert.equal(h.value().length, 2);
  assert.equal(buttons().filter(node => node.props.children === "Añadir").length, 0);
  buttons().find(node => node.props.children === "Quitar").props.onClick();
  assert.equal(h.value()[0].rol, "becario");
  assert.equal(contratos.mismasAutorias([investigador], [becario]), false);
  assert.equal(contratos.mismasAutorias([investigador, becario], [becario, investigador]), true);
});

test("Búsqueda y paginación de cinco autores conservan las selecciones pendientes", () => {
  const options = Array.from({ length: 20 }, (_, index) => ({ ...investigador, id: index + 1,
    nombre_apellido: `Ángela Pérez ${index}`, rol: index % 2 ? "becario" : "investigador" }));
  const h = selectorHarness([], options);
  const addButtons = () => h.render().filter(node => node.type === "Button" && node.props.children === "Añadir");
  const search = (value: string) => h.render().find(node => node.type === "input").props.onChange({ target: { value } });
  assert.equal(addButtons().length, 5);
  h.render().find(node => node.type === "Button" && node.props.children === "Siguiente").props.onClick();
  assert.equal(addButtons().length, 5);
  addButtons()[0].props.onClick();
  assert.equal(h.value().length, 1);
  search("perez angela");
  assert.equal(addButtons().length, 5);
  search("A.P.");
  assert.equal(addButtons().length, 5);
  h.render().find(node => node.type === "select").props.onChange({ target: { value: "becario" } });
  assert.equal(addButtons().length, 5);
  h.render().find(node => node.type === "Button" && node.props.children === "Siguiente").props.onClick();
  assert.equal(addButtons().length, 4);
  search("no existe");
  assert.equal(addButtons().length, 0);
  assert.ok(h.render().some(node => node.props.role === "status" && /No hay coincidencias/.test(node.props.children)));
  search("");
  assert.equal(addButtons().length, 5);
  assert.equal(h.value().length, 1);
  const disabledNodes = h.render(true);
  assert.ok(disabledNodes.filter(node => ["input", "select", "Button"].includes(node.type)).every(node => node.props.disabled));
  disabledNodes.find(node => node.type === "Button" && node.props.children === "Añadir").props.onClick();
  assert.equal(h.value().length, 1);
});

for (const [page, route] of [
  ["TrabajosReunionDetalle", "/trabajos-reunion"],
  ["TrabajosRevistasDetalle", "/trabajos-revistas"],
]) {
  test(`${page}: muestra investigador y becario y abre la edición común de autores`, () => {
    const navigations: string[] = [];
    const Detail = load(`src/modules/produccion/pages/${page}.tsx`, {
      react: { useMemo: (factory: any) => factory(), useEffect() {}, useState: (initial: unknown) => [initial, () => {}] },
      "react-router-dom": { useParams: () => ({ id: "8" }), useLocation: () => ({ state: null }),
        useNavigate: () => (path: string) => navigations.push(path) },
      "@tanstack/react-query": { useQuery: (options: any) => ({ data: options.queryKey[0].includes("historial") ? [] : {
        id: 8, titulo_trabajo: "Estudio", enlace: "https://doi.org/10.1234/test", autores: [investigador, becario], activo: true,
      }, isLoading: false, isError: false }) },
      "@/modules/produccion/services/trabajoAutoresServices": contratos,
      "@/context/AuthContext": { useAuth: () => ({ canEditRecords: () => true }) },
      "@/modules/produccion/hooks/useTiposReunion": { useTiposReunion: () => ({ tipos: [] }) },
      "@/modules/produccion/hooks/useTiposRevista": { useTiposRevista: () => ({ tipos: [] }) },
      "@/modules/produccion/utils/trabajoRevistaHistory": {
        presentTrabajoRevistaHistoryItems: (items: unknown[]) => items,
        formatTrabajoRevistaHistoryEntry: () => null,
      },
      "@/modules/shared/hooks/useAuditoria": { useAuditoria: () => ({ nombreCreador: "Gestor" }) },
      "@/utils/format": { toTitleCase: (text: string) => text },
      "@/utils/dateTime": { formatFecha: () => "-", formatFechaHora: () => "-" },
    }).default;
    const nodes = walk(Detail());
    const text = nodes.filter(node => node.type === "p").map(node => JSON.stringify(node.props.children)).join(" ");
    const link = nodes.find(node => node.type === "a" && node.props.target === "_blank");
    assert.equal(link.props.href, "https://doi.org/10.1234/test");
    assert.equal(link.props.rel, "noopener noreferrer");
    assert.match(JSON.stringify(link.props.children), /pestaña nueva/);
    assert.match(text, /Autores/);
    if (page === "TrabajosReunionDetalle") assert.match(text, /Fecha de presentación/);
    assert.match(text, /Ana \(Investigador\), Luis \(Becario\)/);
    const edit = nodes.find(node => node.type === "Button" && node.props.children === "Editar");
    assert.ok(edit);
    edit.props.onClick();
    assert.equal(navigations[0], `${route}/8/editar`);
  });
}

for (const [page, serviceFile, getName, updateName, createName, route] of [
  ["TrabajosReunionForm", "trabajosReunionServices", "getTrabajoReunionById", "updateTrabajoReunion", "createTrabajoReunion", "/trabajos-reunion"],
  ["TrabajosRevistasForm", "trabajosRevistasServices", "getTrabajoRevistaById", "updateTrabajoRevista", "createTrabajoRevista", "/trabajos-revistas"],
]) {
  test(`${page}: guardado único de diferencias, eliminación diferida y edición sin cambios`, async () => {
    let cursor = 0;
    const states: any[] = [], refs: any[] = [], effects: Array<() => void> = [];
    let initialData: any = { id: 8, titulo_trabajo: "Estudio", nombre_reunion: "Congreso", nombre_revista: "Revista",
      procedencia: "Argentina", editorial: "Editorial", issn: "1234-5678", pais: "Argentina",
      fecha_presentacion: "2026-03-20", fecha_publicacion: "2026-03-20",
      tipo_reunion: { id: 1 }, tipo_revista: { id: 1 }, autores: [investigador], activo: true };
    let params: any = { id: "8" };
    let mutation: any;
    let calls = 0;
    let saved: any;
    const navigations: any[] = [];
    const Form = load(`src/modules/produccion/pages/${page}.tsx`, {
      react: { useEffect(effect: () => void) { effects.push(effect); }, useRef(initial: unknown) {
        const index = cursor++; return refs[index] ??= { current: initial };
      }, useState(initial: unknown) {
        const index = cursor++; if (!(index in states)) states[index] = initial;
        return [states[index], (value: any) => { states[index] = typeof value === "function" ? value(states[index]) : value; }];
      } },
      "react-router-dom": { useParams: () => params, useNavigate: () => (...args: any[]) => navigations.push(args) },
      "@tanstack/react-query": { useQueryClient: () => ({ invalidateQueries: async () => {} }),
        useQuery: () => ({ data: initialData, isLoading: false, isError: false }),
        useMutation: (options: any) => { mutation = options; return { isPending: false,
          mutateAsync: async (payload: any) => { const result = await options.mutationFn(payload); await options.onSuccess(result); return result; } }; } },
      [`@/modules/produccion/services/${serviceFile}`]: { [getName]: () => initialData,
        [updateName]: async (_id: number, body: any) => { calls++; saved = body; return { id: 8 }; },
        [createName]: async (body: any) => { calls++; saved = body; return { id: 9 }; } },
      "@/modules/produccion/services/trabajoAutoresServices": contratos,
      "@/modules/produccion/hooks/useIntegrantesAutores": { useIntegrantesAutores: () => ({ data: [investigador, becario] }) },
      "@/modules/produccion/hooks/useTiposReunion": { useTiposReunion: () => ({ tipos: [] }) },
      "@/modules/produccion/hooks/useTiposRevista": { useTiposRevista: () => ({ tipos: [] }) },
      "@/modules/grupo/hooks/useUctGuard": { useUctGuard: () => ({ uct: { id: 1 } }) },
      "@/context/AuthContext": { useAuth: () => ({ canCreateRecords: () => true, canEditRecords: () => true }) },
      "@/utils/format": { toTitleCase: (text: string) => text },
    }).default;
    const render = () => { cursor = 0; effects.length = 0; const nodes = walk(Form()); effects.splice(0).forEach(effect => effect()); return nodes; };
    const selector = () => render().find(node => node.type === "IntegrantesAutoresField");
    const submit = () => render().find(node => node.type === "form").props.onSubmit({ preventDefault() {} });
    render(); render();
    if (page === "TrabajosReunionForm") assert.ok(render().some(node => node.props.label === "Fecha de presentación"));
    await submit();
    assert.equal(calls, 0);
    assert.equal(navigations.at(-1)[0], `${route}/8`);
    selector().props.onChange([investigador, becario]);
    assert.equal(calls, 0); // Relation changes remain local until Save.
    initialData = { ...initialData }; // Background refetch must not overwrite draft authors.
    assert.equal(selector().props.value[1].rol, "becario");
    await submit();
    assert.equal(calls, 1);
    assert.equal(JSON.stringify(saved), '{"autores":[{"id":1,"rol":"investigador"},{"id":1,"rol":"becario"}]}');
    assert.equal(navigations.at(-1)[0], `${route}/8`);
    assert.match(navigations.at(-1)[1].state.successMessage, /actualizado con éxito/);
    selector().props.onChange([becario]);
    assert.equal(calls, 1);
    await submit();
    assert.equal(calls, 2);
    assert.equal(JSON.stringify(saved), '{"autores":[{"id":1,"rol":"becario"}]}');
    // Creation uses the same endpoint payload and returns to Home.
    params = {};
    render();
    await submit();
    assert.equal(navigations.at(-1)[0], route);
    assert.equal(saved.autores[0].rol, "becario");
    const inputEnlace = () => render().find(node => node.type === "input" && node.props.type === "url");
    inputEnlace().props.onChange({ target: { value: "javascript:alert(1)" } });
    const before = calls;
    await submit();
    assert.equal(calls, before);
    assert.ok(render().find(node => node.props.name === "enlace").props.error);
    inputEnlace().props.onChange({ target: { value: " https://doi.org/10.1234/test " } });
    await submit();
    assert.equal(saved.enlace, "https://doi.org/10.1234/test");
    params = { id: "8" };
    initialData = { ...initialData, enlace: saved.enlace };
    inputEnlace().props.onChange({ target: { value: "" } });
    await submit();
    assert.equal(saved.enlace, null);

  });
}


test("ISS-13: service normaliza fechas antiguas y envía únicamente fecha_presentacion", async () => {
  let saved: any;
  const service = load("src/modules/produccion/services/trabajosReunionServices.ts", {
    "@/lib/http": { http: async (_path: string, options: any) => {
      if (options?.body) saved = JSON.parse(options.body);
      return { id: 8, fecha_inicio: "2025-12-31" };
    } },
  });
  const trabajo = await service.getTrabajoReunionById(8);
  assert.equal(trabajo.fecha_presentacion, "2025-12-31");
  assert.equal(trabajo.fecha_inicio, undefined);
  await service.updateTrabajoReunion(8, { fecha_presentacion: "2026-01-01" });
  assert.equal(JSON.stringify(saved), '{"fecha_presentacion":"2026-01-01"}');
});

test("ISS-17: reuniones informa fechas programadas y oculta referencias internas", () => {
  const source = readFileSync(
    "src/modules/produccion/pages/TrabajosReunionForm.tsx",
    "utf8",
  );

  assert.match(source, /Puede indicar una presentación programada\./);
  assert.doesNotMatch(source, /includeTrackingReference/);
  assert.doesNotMatch(source, /maxDate=\{new Date\(\)\}/);
});

test("ISS-14: enlace opcional valida protocolo, longitud y apertura segura", () => {
  const { errorEnlace, enlaceSeguro } = load("src/modules/produccion/utils/trabajoEnlace.ts");
  for (const url of ["", "  ", "http://example.org", "https://doi.org/10.1234/test", "https://example.org/" + "a".repeat(2028)]) assert.equal(errorEnlace(url), undefined);
  for (const url of ["javascript:alert(1)", "ftp://example.org", "//example.org", "https://", "https://user:pass@example.org", "https://@example.org", "https://example.org:99999", "https://example.org/a b", "https://%", "https://<invalid>", "https://invalid_host/", "https://example.org/" + "a".repeat(2029)]) {
    assert.ok(errorEnlace(url), url);
    assert.equal(enlaceSeguro(url), null);
  }
  assert.equal(enlaceSeguro(null), null);
});
