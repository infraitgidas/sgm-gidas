import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const source = readFileSync("src/components/Table.tsx", "utf8");
const code = ts.transpileModule(source, { compilerOptions: {
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
} }).outputText;
const module = { exports: {} as any };
runInNewContext(code, { module, exports: module.exports, require: (name: string) =>
  name === "@/components/LoadingSkeleton"
    ? { default: ({ label }: { label: string }) => createElement("div", { role: "status" }, label) }
    : require(name)
});
const Table = module.exports.default;
const TableRowActionButton = module.exports.TableRowActionButton;

const columns = [
  { id: "name", header: "Nombre", sortable: true, render: (row: { name: string }) => row.name },
  { id: "secondary", header: "Secundaria", priority: "secondary", render: () => "Dato" },
];

function render(props: Record<string, unknown> = {}) {
  return renderToStaticMarkup(createElement(Table, {
    caption: "Personas", columns, rows: [{ id: 1, name: "Ana" }], getRowId: (row: { id: number }) => row.id,
    page: 1, totalPages: 2, totalRecords: 10, onPageChange() {}, sortKey: "name", sortDirection: "asc",
    expandedRowId: 1, renderExpanded: () => createElement("p", {}, "Contenido expandido"),
    onToggleRow() {}, getExpandLabel: (_row: unknown, expanded: boolean) => expanded ? "Ocultar detalle" : "Mostrar detalle",
    onRowClick() {}, getRowTitle: () => "Ver detalle de Ana",
    ...props,
  }));
}

test("Table renderiza semantica, orden controlado, expansion y paginacion accesible", () => {
  const html = render();
  assert.match(html, /<caption class="sr-only">Personas<\/caption>/);
  assert.match(html, /scope="col"/);
  assert.match(html, /aria-sort="ascending"/);
  assert.match(html, /Contenido expandido/);
  assert.match(html, /aria-expanded="true"/);
  assert.match(html, /aria-label="Ocultar detalle"/);
  assert.match(html, /title="Ver detalle de Ana"/);
  assert.match(html, /cursor-pointer/);
  assert.match(html, /aria-label="Paginación de la tabla"/);
  assert.match(html, /aria-current="page"/);
  assert.match(html, /hidden md:table-cell/);
});

test("Table permite expandir varias filas cuando la pantalla controla cada una", () => {
  const html = render({
    rows: [{ id: 1, name: "Ana" }, { id: 2, name: "Eva" }],
    isRowExpanded: () => true,
    renderExpanded: (row: { name: string }) => createElement("p", {}, `Detalle de ${row.name}`),
  });
  assert.match(html, /Detalle de Ana/);
  assert.match(html, /Detalle de Eva/);
  assert.equal((html.match(/aria-expanded="true"/g) ?? []).length, 2);
});

test("Table permite saltar encabezados y usa una sola parada de teclado para ordenar", () => {
  const html = render({ columns: [
    { id: "name", header: "Nombre", sortable: true, render: (row: { name: string }) => row.name },
    { id: "other", header: "Otro", sortable: true, render: () => "Dato" },
  ] });
  assert.match(html, /Saltar los encabezados e ir al primer resultado/);
  assert.equal((html.match(/tabindex="0"/g) ?? []).length, 1);
  assert.equal((html.match(/tabindex="-1"/g) ?? []).length, 2);
});

test("Table presenta estados uniformes y recuperables", () => {
  assert.match(render({ loading: true }), /Cargando información/);
  assert.match(render({ rows: [], totalRecords: 0, totalPages: 0 }), /No hay registros para mostrar/);
  const error = render({ error: true, onRetry() {} });
  assert.match(error, /role="alert"/);
  assert.match(error, /Reintentar/);
});

test("Table conserva el contenido y anuncia una actualizacion paginada", () => {
  const html = render({ refreshing: true });
  assert.match(html, /Ana/);
  assert.match(html, /aria-busy="true"/);
  assert.match(html, /opacity-60/);
  assert.match(html, /Actualizando resultados/);
});

test("las acciones de fila muestran icono y una leyenda configurable", () => {
  const defaultDelete = renderToStaticMarkup(createElement(TableRowActionButton, { action: "delete" }));
  const personalDelete = renderToStaticMarkup(createElement(TableRowActionButton, { action: "delete", label: "Dar de baja" }));

  assert.match(defaultDelete, />Eliminar<\/span>/);
  assert.match(defaultDelete, /text-rose-700/);
  assert.match(personalDelete, />Dar de baja<\/span>/);
});
