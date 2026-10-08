import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import ts from "typescript";

const require = createRequire(import.meta.url);
import { formatTransferenciaHistory, presentTransferenciaHistory } from "../src/modules/transferencia/utils/transferenciaHistory.ts";

test("el historial presenta adoptantes por nombre y oculta inicializaciones", () => {
  const event = { id: 1, campo: "adoptantes", valor_nuevo: { accion: "desvincular", detalle: { nombre: "Municipalidad" } } };
  assert.deepEqual(formatTransferenciaHistory(event), { title: "Adoptante desvinculado", description: "Municipalidad" });
  assert.deepEqual(presentTransferenciaHistory([{ id: 2, campo: "accion" }, { id: 3, campo: "monto", valor_anterior: null, valor_nuevo: 100 }, event]), [event]);
  assert.doesNotMatch(formatTransferenciaHistory({ id: 4, campo: "grupo_utn_id", valor_anterior: { id: 1 }, valor_nuevo: { id: 2 } }).description, /\[object Object\]|\bID \d+/);
});


// Exercise page transitions while the next server response is still pending.
function loadPagedHome(file: string) {
  const values: any[] = [], dependencies: any[][] = [], effects: Array<() => void> = [];
  let cursor = 0, effectCursor = 0, waiting = false;
  const params: any[] = [];
  const memory = { ids: [1, 2, 10, 11], periodo: "2026" };
  const options = { anio: [{ value: "2025", label: "2025" }, { value: "2026", label: "2026" }],
    autor: [{ value: "Autora", label: "Autora" }], curso: [], institucion: [], investigador: [],
    grado: [], rol: [], tipo: [], grupo: [] };
  const navigate = () => {};
  const location = { pathname: "/list", state: {} };
  const module = { exports: {} as any };
  const code = ts.transpileModule(readFileSync(file, "utf8"), { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
    if (name === "react") return {
      useState(initial: any) {
        const index = cursor++;
        if (!(index in values)) values[index] = initial;
        return [values[index], (next: any) => { values[index] = typeof next === "function" ? next(values[index]) : next; }];
      },
      useMemo: (fn: () => any) => fn(),
      useEffect(fn: () => void, deps: any[]) {
        const index = effectCursor++;
        if (!dependencies[index] || deps.some((value, n) => !Object.is(value, dependencies[index][n]))) {
          dependencies[index] = deps;
          effects.push(fn);
        }
      },
    };
    if (name === "@tanstack/react-query") return {
      useQueryClient: () => ({ invalidateQueries: async () => {} }),
      useQuery(config: any) {
        if (!config.queryKey.includes("table")) return { data: [], isLoading: false };
        const query = config.queryKey[2];
        params.push(query);
        const ids = query.page === 2 ? [10, 11] : Array.from({ length: 9 }, (_, n) => n + 1);
        return { data: waiting ? undefined : { data: ids.map(id => ({ id, titulo: `Documento ${id}`,
          curso: `Curso ${id}`, denominacion: `Actividad ${id}`, autores: [], activo: true })),
          meta: { total: 11, total_pages: 2, options } }, isLoading: waiting, isFetching: waiting,
          isError: false, refetch: () => {} };
      },
    };
    if (name === "react-router-dom") return { useLocation: () => location, useNavigate: () => navigate };
    if (name === "@/context/AuthContext") return { useAuth: () => ({ canCreateRecords: () => false,
      canEditRecords: () => false, canDeleteRecords: () => false }) };
    if (name === "@/lib/memoriaSectionFilter") return { getMemoriaSectionFilter: () => memory };
    if (name.startsWith("@/components/")) return { default: name,
      TableActionButton: "button", TableActions: "div", TableFilterChip: "button",
      TableRowActionButton: "button", TableSearch: "input", TableToolbar: "div" };
    if (name.startsWith("@/")) return { toTitleCase: (value: string) => value };
    return require(name);
  } });
  const walk = (node: any): any[] => Array.isArray(node) ? node.flatMap(walk)
    : node?.props ? [node, ...walk(node.props.children)] : [];
  return {
    params,
    setWaiting(value: boolean) { waiting = value; },
    render() {
      cursor = 0; effectCursor = 0;
      const tree = module.exports.default();
      const table = walk(tree).find(node => node.type === "@/components/Table");
      while (effects.length) effects.shift()!();
      return table;
    },
  };
}

for (const file of ["src/modules/transferencia/pages/TransferenciasHome.tsx",
  "src/modules/produccion/pages/DocenciaHome.tsx", "src/modules/produccion/pages/DocumentacionHome.tsx"]) {
  test(`${file}: conserva la segunda pagina durante la consulta y el alcance de memoria`, () => {
    const view = loadPagedHome(file);
    let table = view.render();
    assert.equal(table.props.rows.length, 9);
    assert.equal(table.props.totalRecords, 11);
    table.props.onPageChange(2);
    view.setWaiting(true);
    table = view.render();
    assert.equal(table.props.page, 2);
    view.setWaiting(false);
    table = view.render();
    assert.equal(table.props.page, 2);
    assert.equal(table.props.rows.map((row: any) => row.id).join(","), "10,11");
    assert.equal(table.props.totalPages, 2);
    const query = view.params.at(-1);
    assert.equal(query.page, 2);
    assert.equal(query.activos, "all");
    assert.equal(query.ids.join(","), "1,2,10,11");
  });
}


test("los services paginados envian todos los filtros e IDs vacios sin perder la normalizacion", async () => {
  const cases = [
    { file: "src/modules/transferencia/services/transferenciasServices.ts", name: "getTransferenciasPage",
      row: { id: 10, numero_transferencia: 25, denominacion: "Convenio", adoptantes: [] },
      fields: { filters: { tipo: "Asistencia & Desarrollo", grupo: "GIDAS", anio: "2026" } },
      key: "filter_tipo", value: "Asistencia & Desarrollo", mapped: "numeroTransferencia", expected: 25 },
    { file: "src/modules/produccion/services/actividadDocenciaServices.ts", name: "getActividadesDocenciaPage",
      row: { id: 10, grado_academico: { id: 2, nombre: "Doctorado" }, rol_actividad: "Profesor" },
      fields: { sort: "grado", filters: { grado: "Doctorado" } },
      key: "filter_grado", value: "Doctorado", mapped: "grado_academico", expected: "Doctorado" },
    { file: "src/modules/produccion/services/documentacionServices.ts", name: "getDocumentacionPage",
      row: { id: 10, anio: "2026", autores: [{ id: 2, nombre_apellido: "Autora" }] },
      fields: { autor: "Apellido, Nombre", anio: "2026" },
      key: "filter_autor", value: "Apellido, Nombre", mapped: "anio", expected: 2026 },
  ];
  for (const config of cases) {
    let url = "";
    const meta = { total: 11, total_pages: 2, options: { anio: [{ value: "2025", label: "2025" }] } };
    const module = { exports: {} as any };
    const code = ts.transpileModule(readFileSync(config.file, "utf8"), { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
    } }).outputText;
    runInNewContext(code, { module, exports: module.exports, URLSearchParams, require: (name: string) => {
      if (name === "@/lib/http") return { http: async (path: string) => { url = path; return { data: [config.row], meta }; } };
      if (name === "./tiposContratoService") return { isMockMode: () => false };
      return require(name);
    } });
    const result = await module.exports[config.name]({ page: 2, activos: "all", direction: "desc",
      q: "Texto & instituciones", ids: [], ...config.fields });
    const query = new URL(url, "http://localhost").searchParams;
    assert.equal(query.get("page"), "2");
    assert.equal(query.get("per_page"), "9");
    assert.equal(query.get("view"), "table");
    assert.equal(query.get("ids"), "");
    assert.equal(query.get("activos"), "all");
    assert.equal(query.get("direction"), "desc");
    assert.equal(query.get("q"), "Texto & instituciones");
    assert.equal(query.get(config.key), config.value);
    assert.equal(result.data[0][config.mapped], config.expected);
    assert.equal(result.meta, meta);
  }
});
