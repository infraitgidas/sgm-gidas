import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const memoria = (id: number) => ({
  id,
  grupo_utn_nombre: "UCT",
  periodo_inicio: "2025-01-01",
  periodo_fin: "2025-12-31",
  version_actual_id: id * 10,
  version_actual: { id: id * 10, numero_version: 2, estado: "cerrada" },
  cantidad_versiones: 2,
});

function renderHome(list: ReturnType<typeof memoria>[], detail: object | null = null, canManage = true) {
  const state: unknown[] = [];
  let cursor = 0;
  const queries: Array<{ queryKey: unknown[]; enabled?: boolean }> = [];
  const destinations: string[] = [];
  const module = { exports: {} as { default: () => any } };
  const source = readFileSync("src/modules/memorias/pages/MemoriasHome.tsx", "utf8");
  const code = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  runInNewContext(code, {
    module,
    exports: module.exports,
    require: (name: string) => {
      if (name === "react") return {
        useState(initial: unknown) {
          const index = cursor++;
          if (!(index in state)) state[index] = typeof initial === "function" ? (initial as () => unknown)() : initial;
          return [state[index], (next: any) => { state[index] = typeof next === "function" ? next(state[index]) : next; }];
        },
        useMemo: (factory: () => unknown) => factory(),
        useEffect: () => {},
      };
      if (name === "@tanstack/react-query") return {
        useQueryClient: () => ({ invalidateQueries: async () => {} }),
        useMutation: () => ({ mutateAsync: async () => {}, isPending: false }),
        useQuery: (options: { queryKey: unknown[]; enabled?: boolean }) => {
          queries.push(options);
          return { data: options.queryKey[0] === "memorias" ? list : detail, isLoading: false, isFetching: false, isError: false };
        },
      };
      if (name === "react-router-dom") return {
        useNavigate: () => (path: string) => destinations.push(path),
        useLocation: () => ({ pathname: "/memorias", state: null }),
      };
      if (name === "@/context/AuthContext") return { useAuth: () => ({ isAdmin: () => canManage, isGestor: () => false }) };
      if (name === "@/utils/dateTime") return { formatFecha: (value: string) => value, formatFechaHora: (value: string) => value };
      if (name === "@/lib/httpError") return { getErrorMessage: (_error: unknown, fallback: string) => fallback };
      if (name === "@/modules/memorias/services/memoriasService") return {};
      if (name.startsWith("@/components/")) return { default: name, TableActionButton: "button", TableActions: "div", TableFilterChip: "button", TableRowActionButton: "button", TableSearch: "input", TableToolbar: "div" };
      return require(name);
    },
  });
  const render = () => {
    cursor = 0;
    queries.length = 0;
    return module.exports.default();
  };
  const table = (tree: any) => tree.props.children[0].props.children.find((child: any) => child?.type === "@/components/Table");
  return { render, table, queries, destinations };
}

test("Memorias pagina por nueve períodos y permite abrir varias filas independientes", () => {
  const list = Array.from({ length: 10 }, (_, index) => memoria(index + 1));
  const detail = { ...list[0], versiones: [
    { id: 9, numero_version: 1, estado: "cerrada", fecha_apertura: "2025-01-01" },
    { id: 10, numero_version: 2, estado: "cerrada", fecha_apertura: "2025-02-01" },
  ] };
  const view = renderHome(list, detail);
  let table = view.table(view.render());
  assert.equal(table.props.rows.length, 9);
  assert.equal(table.props.totalRecords, 10);
  assert.equal(table.props.totalPages, 2);
  assert.equal(view.queries.length, 1);

  table.props.onToggleRow(list[0]);
  table.props.onToggleRow(list[1]);
  table = view.table(view.render());
  assert.equal(table.props.isRowExpanded(list[0]), true);
  assert.equal(table.props.isRowExpanded(list[1]), true);
  assert.equal(view.queries.length, 1);
  assert.equal(table.props.rows.length, 9);
  const expanded = table.props.renderExpanded(list[0]);
  const content = expanded.type(expanded.props);
  assert.equal(JSON.stringify(view.queries[1].queryKey), '["memoria",1]');
  assert.equal(content.props.children[1].props.children.length, 2);
  table.props.onToggleRow(list[0]);
  table = view.table(view.render());
  assert.equal(table.props.isRowExpanded(list[0]), false);
  assert.equal(table.props.isRowExpanded(list[1]), true);
  assert.deepEqual(view.destinations, []);
});

test("Las acciones de versión respetan su estado y el permiso de gestión", () => {
  const item = memoria(1);
  const detail = { ...item, version_actual_id: 10, versiones: [
    { id: 9, numero_version: 1, estado: "cerrada", fecha_apertura: "2025-01-01" },
    { id: 10, numero_version: 2, estado: "abierta", fecha_apertura: "2025-02-01" },
  ] };
  const view = renderHome([item], detail, false);
  let table = view.table(view.render());
  table.props.onToggleRow(item);
  table = view.table(view.render());
  const expanded = table.props.renderExpanded(item);
  const versions = expanded.type(expanded.props).props.children[1].props.children;
  const closedAction = versions[0].props.children[1].props.children[0];
  assert.equal(closedAction.props.title, "Ver detalle");
  closedAction.props.onClick();
  assert.deepEqual(view.destinations, ["/memorias/1/versiones/9"]);
  assert.equal(versions[1].props.children[1].props.children[1], false);
});

test("Las cuatro acciones bloquean cambios históricos y respetan las transiciones", () => {
  for (const estado of ["abierta", "en revision", "cerrada"]) {
    const item = memoria(1);
    const detail = { ...item, versiones: [
      { id: 9, numero_version: 1, estado: "cerrada" },
      { id: 10, numero_version: 2, estado },
    ] };
    const view = renderHome([item], detail);
    const expanded = view.table(view.render()).props.renderExpanded(item);
    const versions = expanded.type(expanded.props).props.children[1].props.children;
    const historical = versions[0].props.children[1].props.children[1].props.children;
    assert.ok(historical.every((button: any) => button.props.disabled));
    const actions = versions[1].props.children[1].props.children;
    assert.equal(actions[0].props.title, "Ver detalle");
    const [reabrir, cerrar, revision] = actions[1].props.children;
    assert.equal(reabrir.props.disabled, estado !== "cerrada");
    assert.equal(cerrar.props.disabled, estado === "cerrada");
    assert.equal(revision.props.disabled, estado !== "abierta");
  }
});
