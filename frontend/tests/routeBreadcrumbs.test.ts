import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import ts from "typescript";
import * as catalogNavigation from "../src/modules/catalogos/utils/catalogNavigation.ts";
import * as memoriaNavigation from "../src/lib/memoriaNavigation.ts";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";

const require = createRequire(import.meta.url);
const module = { exports: {} as typeof import("../src/modules/shared/utils/routeBreadcrumbs.ts") };
const code = ts.transpileModule(readFileSync(new URL("../src/modules/shared/utils/routeBreadcrumbs.ts", import.meta.url), "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
runInNewContext(code, { module, exports: module.exports, Array, Object, require: (name: string) =>
  name === "@/modules/catalogos/utils/catalogNavigation" ? catalogNavigation : require(name) });
// Normaliza los objetos del contexto VM para conservar las comparaciones del resolvedor.
const getRouteBreadcrumbs = (pathname: string, state?: unknown) =>
  JSON.parse(JSON.stringify(module.exports.getRouteBreadcrumbs(pathname, state)));

test("Catálogos incluye la pantalla de origen y recupera su breadcrumb al volver", () => {
  const context = { memoriaFilter: { memoriaId: 2 }, searchReturnTo: "/busqueda?q=ana" };
  for (const [pathname, labels] of [
    ["/personal", ["Inicio", "Personal", "Catálogos"]],
    ["/proyectos/7/editar", ["Inicio", "Proyectos", "Detalle", "Editar", "Catálogos"]],
    ["/memorias/2/versiones/3", ["Inicio", "Memorias", "Detalle", "Versión", "Catálogos"]],
    ["/busqueda", ["Inicio", "Búsqueda", "Catálogos"]],
  ] as const) {
    const state = catalogNavigation.buildCatalogNavigationState({ pathname, search: "?page=2", hash: "#datos", state: context });
    const items = getRouteBreadcrumbs("/catalogos", state);
    assert.deepEqual(items.map((item: any) => item.label), labels);
    assert.equal(items.at(-2).to, `${pathname}?page=2#datos`);
    assert.deepEqual(items.at(-2).state, context);
    assert.equal(items.at(-1).to, undefined);
    const destination = catalogNavigation.getCatalogReturn(state);
    assert.deepEqual(getRouteBreadcrumbs(destination.pathname, destination.state), getRouteBreadcrumbs(pathname, context));
  }
  for (const state of [undefined, { catalogosReturnTo: { pathname: "//otro.test" } },
    { catalogosReturnTo: { pathname: "/catalogos" } }, { catalogosReturnTo: { pathname: "/ruta-inexistente" } }]) {
    assert.deepEqual(getRouteBreadcrumbs("/catalogos", state), [{ label: "Inicio", to: "/inicio" }, { label: "Catálogos" }]);
  }
});

test("el breadcrumb renderizado enlaza el origen con su contexto y marca Catálogos como pantalla actual", () => {
  const links: any[] = [];
  const component = { exports: {} as any };
  const source = readFileSync(new URL("../src/modules/shared/components/RouteBreadcrumbs.tsx", import.meta.url), "utf8");
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  runInNewContext(code, { module: component, exports: component.exports, require: (name: string) => {
    if (name === "@/modules/shared/utils/routeBreadcrumbs") return module.exports;
    if (name === "@/lib/memoriaNavigation") return memoriaNavigation;
    if (name === "react-router-dom") return { ...require(name), Link: (props: any) => {
      links.push(props); return createElement(require(name).Link, props);
    } };
    return require(name);
  } });
  const context = { memoriaFilter: { memoriaId: 2 } };
  const state = catalogNavigation.buildCatalogNavigationState({ pathname: "/proyectos/7/editar", search: "?page=2", hash: "#datos", state: context });
  const html = renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [{ pathname: "/catalogos", state }] },
    createElement(component.exports.default)));
  assert.match(html, /aria-current="page"[^>]*>Catálogos/);
  assert.equal((html.match(/aria-current="page"/g) ?? []).length, 1);
  const originLink = links.find(link => link.to === "/proyectos/7/editar?page=2#datos");
  assert.deepEqual(originLink.state, context);
  assert.ok(links.every(link => !link.state?.catalogosReturnTo));
});

test("resuelve detalle y edición de Personal con enlaces a rutas reales", () => {
  assert.deepEqual(getRouteBreadcrumbs("/personal/investigador/42"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Personal", to: "/personal" },
    { label: "Detalle" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/personal/investigador/42/editar"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Personal", to: "/personal" },
    { label: "Detalle", to: "/personal/investigador/42" },
    { label: "Editar" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/becarios/7/editar")[2], {
    label: "Detalle",
    to: "/becarios/7",
  });
});

test("becas refleja el origen del becario y restaura su contexto en detalle y edición", () => {
  const originState = {memoriaFilter: {anio: 2026}, memoriaReturnTo: "/memorias/1", searchReturnTo: "/busqueda?q=Ana"};
  const state = {becarioReturnTo: {pathname: "/personal/becario/3", search: "?tab=datos", hash: "#becas", state: originState}};
  const detail = getRouteBreadcrumbs("/becas/7", state);
  assert.deepEqual(detail.map(item => item.label), ["Inicio", "Personal", "Becario", "Beca"]);
  assert.equal(detail[2].to, "/personal/becario/3?tab=datos#becas");
  assert.deepEqual(detail[2].state, originState);
  assert.equal(detail.at(-1)?.to, undefined);
  const edit = getRouteBreadcrumbs("/becas/7/editar", state);
  assert.deepEqual(edit.map(item => item.label), ["Inicio", "Personal", "Becario", "Beca", "Editar"]);
  assert.equal(edit[3].to, "/becas/7");
  assert.deepEqual(edit[3].state, state);
  for (const origin of [undefined, null, {}, {pathname: "https://example.com"}, {pathname: "/personal/becario/0"}])
    assert.deepEqual(getRouteBreadcrumbs("/becas/7", {becarioReturnTo: origin}), getRouteBreadcrumbs("/becas/7"));
  assert.deepEqual(getRouteBreadcrumbs("/becas", state), getRouteBreadcrumbs("/becas"));
  assert.deepEqual(getRouteBreadcrumbs("/becas/nueva", state), getRouteBreadcrumbs("/becas/nueva"));
});

test("resuelve rutas de edición de los módulos y el alias anterior de Proyectos", () => {
  assert.deepEqual(getRouteBreadcrumbs("/trabajos-reunion/8/editar"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Trabajos en Reunión Científica", to: "/trabajos-reunion" },
    { label: "Detalle", to: "/trabajos-reunion/8" },
    { label: "Editar" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/proyectos/5/editar")[2], {
    label: "Detalle",
    to: "/proyectos/5",
  });
  assert.deepEqual(getRouteBreadcrumbs("/proyectos/editar/5")[2], {
    label: "Detalle",
    to: "/proyectos/5",
  });
});

test("versiones de Memorias omite el segmento sin página y oculta los identificadores", () => {
  assert.deepEqual(getRouteBreadcrumbs("/memorias/3/versiones/12"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Memorias", to: "/memorias" },
    { label: "Detalle", to: "/memorias/3" },
    { label: "Versión" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/memorias/3"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Memorias", to: "/memorias" },
    { label: "Detalle" },
  ]);
});

test("incluye rutas de primer nivel, altas, acceso público y página inexistente", () => {
  assert.deepEqual(getRouteBreadcrumbs("/inicio"), [{ label: "Inicio" }]);
  assert.deepEqual(getRouteBreadcrumbs("/personal"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Personal" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/usuarios/nuevo"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Usuarios", to: "/usuarios" },
    { label: "Nuevo" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/uct/nueva"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Nueva UCT" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/uct/editar"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Editar UCT" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/login"), [
    { label: "Portada", to: "/" },
    { label: "Iniciar sesión" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/ruta-inexistente"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Página no encontrada" },
  ]);
});

test("cubre todas las rutas actuales del router sin exponer IDs en etiquetas", () => {
  const router = readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
  const paths = [...router.matchAll(/path:\s*"([^"]+)"/g)]
    .map((match) => match[1])
    .filter((path) => path !== "*");

  assert.ok(paths.length > 0);
  for (const path of paths) {
    const concretePath = path.startsWith("/") ? path : `/${path.replace(":rol", "investigador").replace(/:id|:versionId/g, "42")}`;
    const items = getRouteBreadcrumbs(concretePath);
    assert.ok(items.length >= 1, `Falta breadcrumb para ${path}`);
    assert.equal(items.at(-1)?.to, undefined, `El destino actual de ${path} debe ser texto`);
    assert.ok(items.every((item) => !/\d/.test(item.label)), `El breadcrumb de ${path} expone un ID`);
  }
});
