import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);

for (const path of ["personal/PersonalHome", "produccion/DocenciaHome", "proyectos/ProyectosHome", "memorias/MemoriasHome"]) {
  test(`${path}: seleccionar y limpiar estado conserva el contrato y la clase usa desplegable`, () => {
    const [moduleName, page] = path.split("/");
    const states = new Map<string, any>();
    const selectors = new Map<string, any>();
    const source = readFileSync(`src/modules/${moduleName}/pages/${page}.tsx`, "utf8");
    const code = ts.transpileModule(source, { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    } }).outputText;
    const module = { exports: {} as any };
    runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
      if (name === "@/modules/shared/hooks/useHomeState") return {
        useHomeState: (key: string, initial: any) => {
          if (!states.has(key)) states.set(key, initial);
          return [states.get(key), (next: any) => states.set(key, typeof next === "function" ? next(states.get(key)) : next)];
        }, useHomeFilterEffect: () => {},
      };
      if (name === "@/context/AuthContext") return { useAuth: () => ({
        canCreateRecords: () => false, canEditRecords: () => false, canDeleteRecords: () => false,
        isGestor: () => false, isAdmin: () => false,
      }) };
      if (name === "react-router-dom") return {
        useLocation: () => ({ pathname: "/test", search: "", state: null }),
        useNavigate: () => () => {}, useSearchParams: () => [new URLSearchParams()],
      };
      if (name === "@tanstack/react-query") return {
        useQueryClient: () => ({}), useMutation: () => ({}),
        useQuery: () => ({ data: page === "DocenciaHome" ? { data: [], meta: { options: {}, total_pages: 0 } } : [], isLoading: false }),
      };
      if (name === "@/components/TableFilterSelect") return { default: (props: any) => { selectors.set(props.label, props); return null; } };
      if (name === "@/components/Table") return {
        default: ({ toolbar }: any) => toolbar, TableToolbar: ({ children }: any) => children,
        TableSearch: () => null,
      };
      if (name.startsWith("@/components/")) return { default: () => null };
      if (name === "@/lib/memoriaSectionFilter") return { getMemoriaSectionFilter: () => null };
      if (name === "@/modules/personal/hooks/usePersonal") return { usePersonal: () => ({ list: [], meta: {} }) };
      if (name === "@/modules/proyectos/hooks/useProyectos") return { useProyectosPage: () => ({ list: [], meta: {} }) };
      if (name === "@/modules/proyectos/hooks/useTiposProyecto") return { useTiposProyecto: () => ({ data: [] }) };
      if (name === "@/modules/catalogos/hooks/useFuenteFinanciamiento") return { useFuentesFinanciamiento: () => ({ fuentes: [] }) };
      if (name === "@/utils/dateTime") return { getLocalTodayIso: () => "2026-11-06" };
      if (name.startsWith("@/")) return {};
      return require(name);
    } });
    const render = () => renderToStaticMarkup(React.createElement(module.exports.default));
    render();
    let state = selectors.get("Filtrar por estado");
    assert.equal(state.value, "true");
    assert.deepEqual(Array.from(state.options, (option: any) => option.value), ["true", "false"]);
    state.onValueChange("false"); render();
    assert.equal(selectors.get("Filtrar por estado").value, "false");
    state.onValueChange(undefined); render();
    assert.equal(selectors.get("Filtrar por estado").value, undefined);
    assert.equal(states.get(page === "MemoriasHome" ? "estado" : "activeFilter"), "all");
    if (page === "PersonalHome") {
      selectors.get("Filtrar por clase de personal").onValueChange("BECARIO"); render();
      assert.equal(selectors.get("Filtrar por clase de personal").value, "BECARIO");
      selectors.get("Filtrar por clase de personal").onValueChange(undefined); render();
      assert.equal(states.get("classFilter"), "");
    }
  });
}

test("los homes no ofrecen chips para seleccionar filtros", () => {
  for (const file of readdirSync("src/modules", { recursive: true }).filter(file => String(file).endsWith("Home.tsx"))) {
    const source = readFileSync(`src/modules/${file}`, "utf8");
    assert.doesNotMatch(source, /TableFilterChip/, String(file));
  }
});
