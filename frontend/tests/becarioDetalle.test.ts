import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { getBecaNavigationState } from "../src/modules/recursos/utils/becaNavigation.ts";

const require = createRequire(import.meta.url);
const record = {id: 3, rol: "becario", nombre: "Ana", apellido: "Pérez", nombre_apellido: "Ana Pérez",
  dni: "12345678", cuil: "20-12345678-6", fecha_alta_grupo: "2026-01-01", horas_semanales: 20,
  tipo_formacion: "Grado", activo: true, created_at: null, deleted_at: null, becas: []};

function load(file: string, options: any = {}): any {
  const module = {exports: {} as any};
  let stateIndex = 0;
  const code = ts.transpileModule(readFileSync(file, "utf8"), {compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  }}).outputText;
  runInNewContext(code, {module, exports: module.exports, require: (name: string) => {
    if (name === "react" && file.endsWith("HistorialCambiosCard.tsx")) return {...React,
      useState: () => [stateIndex++ === 0 ? true : options.page ?? 1, () => {}]};
    if (name === "@/components/ui/collapsible") return Object.fromEntries(
      ["Collapsible", "CollapsibleTrigger", "CollapsibleContent"].map(key => [key, ({children}: any) => children]));
    if (name === "react" && file.endsWith("BecasDetalle.tsx")) return {...React, useEffect: (effect: () => void) => options.effects?.push(effect)};
    if (name === "react-router-dom" && /(?:PersonalDetalle|BecasDetalle|BecasForm)\.tsx$/.test(file)) return {
      useParams: () => ({rol: "becario", id: "3"}), useNavigate: () => options.navigate ?? (() => {}),
      useLocation: () => options.location ?? ({pathname: "/personal/becario/3", search: "", hash: "", state: null}),
    };
    if (name === "react-router-dom" && options.links) return {...require(name), Link: (props: any) => {
      options.links.push(props); return React.createElement(require(name).Link, props);
    }};
    if (name === "@tanstack/react-query") return {
      useQueryClient: () => ({invalidateQueries: async () => {}}),
      useMutation: (config: any) => {options.mutation = config; return {isPending: false};},
      useQuery: ({queryKey}: any) => queryKey[0] === "beca" ? {data: {id: 7, nombre_beca: "Beca", becarios: []}}
      : queryKey[0] === "personal-detalle"
      ? {data: options.data ?? record, isLoading: options.loading, isError: options.error}
      : {data: [], isLoading: options.historyLoading, isError: options.historyError}};
    if (name === "@/context/AuthContext") return {useAuth: () => ({canEditRecords: () => options.canEdit ?? true})};
    if (name === "@/components/Button") return {default: ({children, onClick, ...props}: any) => {
      options.actions?.push({children, onClick}); return React.createElement("button", props, children);
    }};
    if (name === "@/components/SuccessToast") return {default: () => null};
    if (name === "@/components/LoadingSkeleton") return {default: ({label}: any) => React.createElement("p", {role: "status"}, label)};
    if (name === "@/utils/dateTime") return {...load("src/utils/dateTime.ts"), getLocalTodayIso: () => "2026-11-05"};
    if (name === "@/components/HistorialCambiosCard" && file.endsWith("PersonalDetalle.tsx")) return {
      default: ({pageSize}: any) => React.createElement("article", {"data-page-size": pageSize}, "Historial de cambios")};
    if (name.startsWith("@/modules/personal/services/") || name.startsWith("@/modules/recursos/services/")) return {};
    if (name === "@/modules/catalogos/hooks/useFuenteFinanciamiento") return {useFuentesFinanciamiento: () => ({fuentes: []})};
    if (name === "@/components/Field") return {default: ({children}: any) => React.createElement("div", {}, children)};
    if (name.startsWith("@/")) return load(`src/${name.slice(2)}${name.includes("/components/") ? ".tsx" : ".ts"}`, options);
    return require(name);
  }});
  return module.exports;
}

test("becario separa datos y asignaciones compactas, con estados por período y enlaces reales", () => {
  const Section = load("src/modules/personal/components/BecarioDatosSection.tsx").default;
  const html = renderToStaticMarkup(React.createElement(MemoryRouter, {}, React.createElement(Section, {data: {...record, becas: [
    {id: 7, nombre_beca: "Beca activa", fecha_inicio: "2026-01-01", fecha_fin: "2026-11-05", descripcion: "NO MOSTRAR DESCRIPCION", monto_percibido: 123456},
    {id: 8, nombre_beca: "Beca futura", fecha_inicio: "2026-11-06", fecha_fin: "2027-11-05"},
    {id: 9, nombre_beca: "Beca pasada", fecha_inicio: "2025-01-01", fecha_fin: "2026-11-04", monto_percibido: 0},
    {id: 10, nombre_beca: "Beca sin fin", fecha_inicio: "2026-01-01", fecha_fin: null},
  ]}})));
  for (const text of ["Datos del becario", "Becas asignadas", "Ana", "Pérez", "Grado", "Activa", "Próxima", "Finalizada", "Sin fecha de fin"])
    assert.ok(html.includes(text), text);
  assert.match(html, /href="\/becas\/7"/);
  assert.equal((html.match(/>Ver detalle<\/a>/g) ?? []).length, 4);
  assert.doesNotMatch(html, /NO MOSTRAR DESCRIPCION/);
  assert.match(html, /Monto percibido/);
  assert.match(html, /123\.456,00/);
  assert.match(html, /\$[\s\u00a0]*0,00/);
  assert.match(html, /Sin registrar/);
  assert.ok(html.includes("items-start"));
  assert.ok(html.includes("min-width:1000px"));
  assert.match(html, /aria-hidden="true"/);
  const empty = renderToStaticMarkup(React.createElement(MemoryRouter, {}, React.createElement(Section, {data: record})));
  assert.match(empty, /Becas asignadas/);
  assert.match(empty, /Este becario no tiene becas asignadas/);
  assert.doesNotMatch(empty, /Ver detalle/);
});

test("detalle mantiene orden completo, permisos, carga, error y navegación de edición", () => {
  const file = "src/modules/personal/pages/PersonalDetalle.tsx";
  const actions: any[] = [];
  const navigations: any[] = [];
  const Page = load(file, {actions, navigate: (...args: any[]) => navigations.push(args)}).default;
  const html = renderToStaticMarkup(React.createElement(MemoryRouter, {}, React.createElement(Page)));
  const titles = ["Datos del becario", "Becas asignadas", "Historial de cambios", "Auditoría", ">Volver<"];
  titles.forEach((title, index) => {assert.ok(html.includes(title)); if (index) assert.ok(html.indexOf(titles[index - 1]) < html.indexOf(title));});
  assert.match(html, /data-page-size="3"/);
  actions.find(action => action.children === "Editar").onClick();
  assert.equal(navigations[0][0], "/personal/becario/3/editar");
  for (const options of [{canEdit: false}, {data: {...record, activo: false}}, {data: {...record, deleted_at: "2026-11-01"}}]) {
    const View = load(file, options).default;
    assert.doesNotMatch(renderToStaticMarkup(React.createElement(MemoryRouter, {}, React.createElement(View))), />Editar</);
  }
  const Loading = load(file, {loading: true}).default;
  assert.match(renderToStaticMarkup(React.createElement(Loading)), /role="status"/);
  const Error = load(file, {error: true}).default;
  assert.match(renderToStaticMarkup(React.createElement(Error)), /role="alert"/);
  const HistoryError = load(file, {historyError: true}).default;
  assert.match(renderToStaticMarkup(React.createElement(MemoryRouter, {}, React.createElement(HistoryError))), /no pudimos recuperar el historial/);
});

test("historial global conserva formato, icono y paginación de tres elementos", () => {
  const items = Array.from({length: 5}, (_, id) => ({id, campo: `campo_${id}`, valor_anterior: "Antes", valor_nuevo: "Después"}));
  for (const page of [1, 2]) {
    const History = load("src/components/HistorialCambiosCard.tsx", {page}).default;
    const html = renderToStaticMarkup(React.createElement(History, {items}));
    assert.equal((html.match(/Valor anterior:/g) ?? []).length, page === 1 ? 3 : 2);
    assert.ok(html.includes(`Página ${page} de 2`));
    assert.match(html, /lucide-history/);
    assert.match(html, /aria-hidden="true"/);
    assert.match(html, /Ocultar/);
  }
});

test("becario → beca → Volver conserva origen y contexto; acceso directo vuelve al listado", () => {
  const links: any[] = [];
  const Section = load("src/modules/personal/components/BecarioDatosSection.tsx", {links}).default;
  const originContext = {memoriaFilter: {anio: 2026}, memoriaReturnTo: "/memorias/1", searchReturnTo: "/buscar?q=Ana"};
  renderToStaticMarkup(React.createElement(MemoryRouter, {initialEntries: [{pathname: "/personal/becario/3", search: "?tab=datos", hash: "#becas", state: {...originContext, successMessage: "Anterior"}}]},
    React.createElement(Section, {data: {...record, becas: [{id: 7, nombre_beca: "Beca"}]}})));
  assert.equal(links[0].to, "/becas/7");
  assert.deepEqual(JSON.parse(JSON.stringify(links[0].state.becarioReturnTo.state)), originContext);
  const calls: any[] = [];
  const actions: any[] = [];
  const Page = load("src/modules/recursos/pages/BecasDetalle.tsx", {actions,
    location: {pathname: "/becas/7", search: "", hash: "", state: links[0].state},
    navigate: (...args: any[]) => calls.push(args)}).default;
  renderToStaticMarkup(React.createElement(Page));
  actions.find(action => action.children === "Volver").onClick();
  assert.equal(calls[0][0], "/personal/becario/3?tab=datos#becas");
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0][1].state)), originContext);
  actions.find(action => action.children === "Editar").onClick();
  assert.equal(calls[1][0], "/becas/7/editar");
  assert.equal(calls[1][1].state.becarioReturnTo.pathname, "/personal/becario/3");
  const directActions: any[] = [];
  const Direct = load("src/modules/recursos/pages/BecasDetalle.tsx", {actions: directActions,
    navigate: (...args: any[]) => calls.push(args)}).default;
  renderToStaticMarkup(React.createElement(Direct));
  directActions.find(action => action.children === "Volver").onClick();
  assert.equal(calls.at(-1)[0], "/becas");
  for (const pathname of ["https://example.com", "//example.com", "/personal/becario/3/editar", "/personal/becario/0"])
    assert.equal(getBecaNavigationState({becarioReturnTo: {pathname}}), undefined);
});

test("edición y limpieza de éxito conservan el retorno al becario", async () => {
  const state = {becarioReturnTo: {pathname: "/personal/becario/3", search: "", hash: "", state: {memoriaReturnTo: "/memorias/1"}}};
  const calls: any[] = [];
  const config: any = {actions: [], location: {pathname: "/becas/7/editar", state}, navigate: (...args: any[]) => calls.push(args)};
  const Form = load("src/modules/recursos/pages/BecasForm.tsx", config).default;
  renderToStaticMarkup(React.createElement(Form));
  config.actions.find((action: any) => action.children === "Volver").onClick();
  assert.equal(calls[0][1].state.becarioReturnTo.pathname, "/personal/becario/3");
  await config.mutation.onSuccess({id: 7});
  assert.equal(calls[1][0], "/becas/7");
  assert.equal(calls[1][1].state.becarioReturnTo.pathname, "/personal/becario/3");
  const effects: Array<() => void> = [];
  const Page = load("src/modules/recursos/pages/BecasDetalle.tsx", {effects,
    location: {pathname: "/becas/7", search: "", hash: "", state: calls[1][1].state},
    navigate: (...args: any[]) => calls.push(args)}).default;
  renderToStaticMarkup(React.createElement(Page));
  effects.forEach(effect => effect());
  assert.equal(calls.at(-1)[1].state.becarioReturnTo.pathname, "/personal/becario/3");
  assert.equal(calls.at(-1)[1].state.successMessage, undefined);
});

test("breadcrumb compartido enlaza al becario con su estado original", () => {
  const links: any[] = [];
  const Breadcrumbs = load("src/modules/shared/components/RouteBreadcrumbs.tsx", {links}).default;
  const originState = {memoriaFilter: {anio: 2026}, memoriaReturnTo: "/memorias/1"};
  const state = {becarioReturnTo: {pathname: "/personal/becario/3", search: "?tab=datos", hash: "#becas", state: originState}};
  const html = renderToStaticMarkup(React.createElement(MemoryRouter, {initialEntries: [{pathname: "/becas/7/editar", state}]}, React.createElement(Breadcrumbs)));
  assert.match(html, /aria-label="Ruta de navegación"/);
  assert.match(html, /aria-current="page"[^>]*>Editar/);
  assert.match(html, /href="\/personal\/becario\/3\?tab=datos#becas"/);
  const becario = links.find(link => link.children === "Becario");
  assert.deepEqual(JSON.parse(JSON.stringify(becario.state)), originState);
  assert.equal(links.find(link => link.children === "Beca").state.becarioReturnTo.pathname, "/personal/becario/3");
});
