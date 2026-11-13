import assert from "node:assert/strict";
import test from "node:test";
import { homeStateKey, readHomeValue, writeHomeValue } from "../src/modules/shared/utils/homeState.ts";
import { markSessionActive, markSessionEnded, rememberSessionPath, readSessionReturn, resolveSessionReturn,
  clearSessionNotice, sessionNavigationState } from "../src/modules/auth/utils/sessionNavigation.ts";
import { loadHomeStateHooks } from "./helpers/homeStateHooks.ts";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import ts from "typescript";

class MemoryStorage implements Storage {
  values = new Map<string, string>();
  get length() { return this.values.size; }
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
  clear() { this.values.clear(); }
  key(index: number) { return [...this.values.keys()][index] ?? null; }
}

function harness(storage = new MemoryStorage()) {
  const slots: any[] = [];
  let cursor = 0, userId = 1;
  const effects: Array<() => void> = [];
  const location: any = { pathname: "/personal", search: "", state: null };
  const react = {
    useState(initial: any) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = typeof initial === "function" ? initial() : initial;
      return [slots[index], (action: any) => { slots[index] = typeof action === "function" ? action(slots[index]) : action; }];
    },
    useRef(initial: any) { const index = cursor++; return slots[index] ??= { current: initial }; },
    useCallback(fn: any) { return fn; },
    useMemo(fn: any) { return fn(); },
    useEffect(fn: any, deps: any[]) {
      const index = cursor++;
      if (!slots[index] || deps.some((v, i) => !Object.is(v, slots[index][i]))) { slots[index] = deps; effects.push(fn); }
    },
  };
  const hooks = loadHomeStateHooks(react, { useAuth: () => ({ user: { id: userId } }) }, { useLocation: () => location }, storage);
  return { storage, hooks, location, react, user(id: number) { userId = id; },
    render<T>(callback: () => T): T { cursor = 0; const value = callback(); effects.splice(0).forEach(fn => fn()); return value; } };
}

test("los controles se restauran al remontar, se aislan por usuario, ruta y catálogo y admiten actualizaciones funcionales", () => {
  const first = harness();
  const read = (h: ReturnType<typeof harness>) => h.render(() => h.hooks.useHomeState("filters", { estado: "", anio: "" }));
  let [value, set] = read(first);
  set((previous: any) => ({ ...previous, anio: "2026" }));
  set((previous: any) => ({ ...previous, estado: "todos" }));
  assert.equal(first.storage.length, 1, "se escribe durante el cambio, antes del desmontaje por expiración");
  const restored = harness(first.storage);
  [value] = read(restored);
  assert.equal(JSON.stringify(value), '{"estado":"todos","anio":"2026"}');
  restored.user(2);
  assert.equal(read(restored)[0].anio, "");
  set({ estado: "inactivos", anio: "2024" });
  assert.equal(read(restored)[0].anio, "");
  restored.user(1);
  restored.location.pathname = "/proyectos";
  assert.equal(read(restored)[0].anio, "");
  restored.location.pathname = "/personal";
  assert.equal(read(restored)[0].anio, "2024");
  const catalog = (scope: string) => restored.render(() => restored.hooks.useHomeState("search", "", { scope }));
  catalog("/autores")[1]("Ana");
  assert.equal(catalog("/editoriales")[0], "");
  assert.equal(catalog("/autores")[0], "Ana");
});

test("la página recuperada sobrevive al montaje y solo se reinicia si cambian filtros reales", () => {
  const storage = new MemoryStorage();
  const first = harness(storage);
  first.render(() => first.hooks.useHomeState("page", 1))[1](3);
  const view = harness(storage);
  const render = (filters: object) => view.render(() => {
    const [page, setPage] = view.hooks.useHomeState("page", 1);
    view.hooks.useHomeFilterEffect(() => setPage(1), [filters]);
    return page;
  });
  assert.equal(render({ estado: "todos" }), 3);
  assert.equal(render({ estado: "todos" }), 3);
  render({ estado: "inactivos" });
  assert.equal(render({ estado: "inactivos" }), 1);
});

test("memoria, búsqueda explícita y tipo de informe mantienen ámbitos independientes", () => {
  const h = harness();
  const read = () => h.render(() => h.hooks.useHomeState("search", ""));
  read()[1]("General");
  h.location.search = "?tipo=BECARIO";
  assert.equal(read()[0], "");
  read()[1]("Becarios");
  h.location.search = "";
  h.location.state = { memoriaFilter: { memoriaId: 1, versionId: 2, sectionKey: "personal", ids: [3] } };
  assert.equal(read()[0], "");
  h.location.state = null;
  assert.equal(read()[0], "General");
  h.location.pathname = "/informes/pid";
  assert.equal(read()[0], "");
});

test("estado inválido, versión ajena y almacenamiento bloqueado no impiden consultar", () => {
  const storage = new MemoryStorage(), key = homeStateKey(1, "/personal", "page")!;
  for (const value of ["{", "0", "-2", '"3"', "1.5", "null"]) {
    storage.setItem(key, value);
    assert.equal(readHomeValue(storage, key, "page", 1), 1);
  }
  storage.setItem(key, '"desconocido"');
  assert.equal(readHomeValue(storage, key, "sort", "nombre", { allowed: ["nombre", "fecha"] }), "nombre");
  storage.setItem(key, '{"estado":3}');
  assert.deepEqual(readHomeValue(storage, key, "filters", { estado: "" }), { estado: "" });
  storage.setItem(key, '{"extra":"dato"}');
  assert.deepEqual(readHomeValue(storage, key, "filters", { estado: "" }), { estado: "" });
  assert.equal(homeStateKey(undefined, "/personal", "page"), null);
  assert.notEqual(homeStateKey(1, "/personal", "page"), homeStateKey(2, "/personal", "page"));
  const blocked = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("quota"); } } as unknown as Storage;
  assert.equal(readHomeValue(blocked, key, "page", 1), 1);
  assert.doesNotThrow(() => writeHomeValue(blocked, key, 3));
  assert.doesNotThrow(() => writeHomeValue(undefined, null, 3));
});

test("el reingreso restaura URL y contexto solo para el mismo usuario; logout descarta el destino", () => {
  const storage = new MemoryStorage();
  const state = { memoriaFilter: { source: "memoria", sectionKey: "personal", sectionLabel: "Personal", ids: [1, 2],
    memoriaLabel: "Memoria 2026", memoriaId: 1, versionId: 2 }, successMessage: "No repetir", pendingDelete: 8 };
  markSessionActive(storage, 1);
  rememberSessionPath("/personal?tipo=BECARIO#listado", storage, state);
  markSessionEnded(storage);
  const saved = readSessionReturn(storage)!;
  assert.equal(resolveSessionReturn(saved, 1).path, "/personal?tipo=BECARIO#listado");
  assert.deepEqual(saved.state, { memoriaFilter: state.memoriaFilter });
  assert.deepEqual(resolveSessionReturn(saved, 2), { path: "/inicio" });
  assert.equal(sessionNavigationState({ memoriaFilter: { ids: [] } }), undefined);
  assert.equal(sessionNavigationState({ ...state, memoriaFilter: { ...state.memoriaFilter, ids: ["<script>"] } }), undefined);
  clearSessionNotice(storage);
  assert.equal(readSessionReturn(storage), null);
});

test("un callback anterior al cambio de usuario no contamina el estado nuevo ni el anterior", () => {
  const h = harness();
  const read = () => h.render(() => h.hooks.useHomeState("search", ""));
  const [, oldSet] = read();
  oldSet("Cuenta uno");
  h.user(2);
  assert.equal(read()[0], "");
  oldSet("Cambio tardío");
  assert.equal(read()[0], "");
  h.user(1);
  assert.equal(read()[0], "Cuenta uno");
});

for (const [moduleName, page, route] of [["personal", "PersonalHome", "/personal"], ["proyectos", "ProyectosHome", "/proyectos"]]) {
  test(`${page}: consulta desde el primer render con filtros y página restaurados y conserva la página durante el debounce`, () => {
    const h = harness();
    h.location.pathname = route;
    const scope = JSON.stringify([route, "", "", null]);
    const saved = { search: "Ana", page: 3, activeFilter: "all", sort: "nombre", direction: "asc",
      ...(moduleName === "personal" ? { classFilter: "INVESTIGADOR" } : { typeFilter: 2, sourceFilter: 4 }) };
    for (const [field, value] of Object.entries(saved)) writeHomeValue(h.storage, homeStateKey(1, scope, field), value);
    let request: any;
    const timers: Array<() => void> = [];
    const auth = { useAuth: () => ({ user: { id: 1 }, canCreateRecords: () => true, canEditRecords: () => true,
      canDeleteRecords: () => true, isGestor: () => false }) };
    const router = { useLocation: () => h.location, useNavigate: () => () => {}, useSearchParams: () => [new URLSearchParams()] };
    const hooks = loadHomeStateHooks(h.react, auth, router, h.storage);
    const query = (params: any) => { request = params; return { data: undefined, list: [],
      meta: { total_pages: 0, total: 0 }, isLoading: true, isFetching: true, isError: false }; };
    const dependencies: Record<string, any> = {
      react: h.react, "react-router-dom": router, "@/context/AuthContext": auth,
      "@/modules/shared/hooks/useHomeState": hooks,
      "@tanstack/react-query": { useQueryClient: () => ({}), useQuery: () => ({ data: [], isLoading: false }) },
      "@/modules/personal/hooks/usePersonal": { usePersonal: query },
      "@/modules/proyectos/hooks/useProyectos": { useProyectosPage: query },
      "@/modules/proyectos/hooks/useTiposProyecto": { useTiposProyecto: () => ({ data: [] }) },
      "@/modules/catalogos/hooks/useFuenteFinanciamiento": { useFuentesFinanciamiento: () => ({ fuentes: [] }) },
      "@/lib/memoriaSectionFilter": { getMemoriaSectionFilter: () => null },
    };
    const realRequire = createRequire(import.meta.url);
    const result = { exports: {} as any };
    const code = ts.transpileModule(readFileSync(`src/modules/${moduleName}/pages/${page}.tsx`, "utf8"), {
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    runInNewContext(code, { module: result, exports: result.exports,
      window: { setTimeout(fn: () => void) { timers.push(fn); return 1; }, clearTimeout() {} },
      require(name: string) {
        if (name in dependencies) return dependencies[name];
        if (name.startsWith("@/components/")) return { default: name, TableActions: "div", TableActionButton: "button",
          TableRowActionButton: "button", TableFilterChip: "button", TableSearch: "input", TableToolbar: "div" };
        if (name.startsWith("@/")) return {};
        return realRequire(name);
      } });
    h.render(() => result.exports.default());
    assert.equal(request.page, 3);
    assert.equal(request.search, "Ana");
    assert.equal(request.activos, "all");
    assert.equal(request.sort, "nombre");
    assert.equal(request.direction, "asc");
    if (moduleName === "personal") assert.equal(request.tipo, "INVESTIGADOR");
    else { assert.equal(request.tipoProyectoId, 2); assert.equal(request.fuenteFinanciamientoId, 4); }
    timers.splice(0).forEach(fn => fn());
    h.render(() => result.exports.default());
    assert.equal(request.page, 3);
  });
}
