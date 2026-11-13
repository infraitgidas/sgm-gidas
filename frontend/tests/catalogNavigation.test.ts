import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import ts from "typescript";
import * as navigation from "../src/modules/catalogos/utils/catalogNavigation.ts";

const require = createRequire(import.meta.url);

test("Catálogos vuelve a cada módulo con query, hash y contexto sin repetir mensajes", () => {
  for (const pathname of ["/personal", "/proyectos/7/editar"]) {
    const location = { pathname, search: "?page=2", hash: "#datos", state: {
      successMessage: "Guardado", memoriaFilter: { memoriaId: 3 }, searchReturnTo: "/busqueda?q=ana",
    } };
    const result = navigation.getCatalogReturn(navigation.buildCatalogNavigationState(location));
    assert.deepEqual(result, { ...location, state: {
      memoriaFilter: { memoriaId: 3 }, searchReturnTo: "/busqueda?q=ana",
    } });
    assert.equal(location.state.successMessage, "Guardado");
  }
});

test("reingresar a Catálogos y recargar conserva el origen inicial sin anidar retornos", () => {
  const initial = navigation.buildCatalogNavigationState({ pathname: "/documentacion", search: "", hash: "", state: null });
  const reentry = navigation.buildCatalogNavigationState({ pathname: "/catalogos", search: "", hash: "", state: initial });
  assert.deepEqual(reentry, initial);
  assert.equal(navigation.getCatalogReturn(JSON.parse(JSON.stringify(reentry))).pathname, "/documentacion");
});

test("acceso directo y orígenes externos, inválidos o circulares vuelven a Inicio", () => {
  for (const state of [undefined, null, {}, { catalogosReturnTo: null },
    ...["https://otro.test", "//otro.test", "/\\otro.test", "/catalogos", "/catalogos/", "/a/../catalogos",
      "/%2fexterno", "/%5cexterno", "/catalogos%2f", "/%", 4].map(pathname => ({ catalogosReturnTo: { pathname } }))]) {
    assert.deepEqual(navigation.getCatalogReturn(state), { pathname: "/inicio", search: "", hash: "" });
  }
});

test("el enlace real del menú captura el origen desde dos módulos distintos", () => {
  const source = readFileSync(new URL("../src/components/Sidebar.tsx", import.meta.url), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  for (const pathname of ["/personal", "/proyectos"]) {
    const links: any[] = [];
    const module = { exports: {} as any };
    runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
      if (name === "@/context/AuthContext") return { useAuth: () => ({
        user: { rol: "GESTOR" }, isAdmin: () => false, isGestor: () => true,
      }) };
      if (name === "@/modules/catalogos/utils/catalogNavigation") return navigation;
      if (name === "react-router-dom") return { ...require(name), NavLink: (props: any) => {
        links.push(props); return createElement("a", { href: props.to }, props.children);
      } };
      return require(name);
    } });
    renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [{ pathname, search: "?page=2", hash: "#datos" }] },
      createElement(module.exports.default)));
    const catalogLink = links.find(link => link.to === "/catalogos");
    assert.ok(catalogLink);
    assert.deepEqual(navigation.getCatalogReturn(catalogLink.state), { pathname, search: "?page=2", hash: "#datos", state: undefined });
    assert.equal(links.find(link => link.to === "/proyectos").state, undefined);
  }
});

test("Volver en la página real usa el origen guardado o Inicio y reemplaza Catálogos", () => {
  const source = readFileSync(new URL("../src/modules/catalogos/pages/CatalogosHome.tsx", import.meta.url), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  for (const pathname of ["/personal", "/proyectos", null]) {
    const actions: any[] = [];
    const calls: any[] = [];
    const module = { exports: {} as any };
    runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
      if (name === "react-router-dom") return {
        useLocation: () => ({ state: pathname ? { catalogosReturnTo: { pathname, search: "?page=2", hash: "#datos", state: { source: "consulta" } } } : null }),
        useNavigate: () => (...args: any[]) => calls.push(args),
      };
      if (name === "react/jsx-runtime") {
        const runtime = require(name);
        const wrap = (fn: any) => (type: any, ...args: any[]) => type?.name === "CatalogPanel" ? null : fn(type, ...args);
        return { ...runtime, jsx: wrap(runtime.jsx), jsxs: wrap(runtime.jsxs) };
      }
      if (name === "@/modules/catalogos/utils/catalogNavigation") return navigation;
      if (name === "@/modules/shared/hooks/useHomeState") return { useHomeState: (_key: string, value: unknown) => [value, () => {}] };
      if (name === "@/modules/catalogos/hooks/useCatalogDraft") return { useCatalogDraft: () => ({ ready: true }) };
      if (name === "@/context/AuthContext") return { useAuth: () => ({
        canCreateRecords: () => true, canEditRecords: () => true, canDeleteRecords: () => true,
      }) };
      if (name === "@/components/Button") return { default: (props: any) => {
        actions.push(props); return createElement("button", {}, props.children);
      } };
      if (name === "@/components/Field") return { default: ({ children }: any) => children };
      if (name.startsWith("@/")) return {};
      return require(name);
    } });
    renderToStaticMarkup(createElement(module.exports.default));
    actions.find(action => action.children === "Volver").onClick();
    assert.equal(calls.length, 1);
    assert.equal(calls[0][0].pathname, pathname ?? "/inicio");
    assert.equal(calls[0][0].search, pathname ? "?page=2" : "");
    assert.equal(calls[0][0].hash, pathname ? "#datos" : "");
    assert.equal(calls[0][1].state?.source, pathname ? "consulta" : undefined);
    assert.equal(calls[0][1].replace, true);
  }
});
