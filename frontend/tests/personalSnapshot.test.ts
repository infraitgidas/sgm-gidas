import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
function load(file: string, page = 1): any {
  const module = { exports: {} as any };
  const code = ts.transpileModule(readFileSync(file, "utf8"), { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
    if (name === "react" && file.includes("PersonalSnapshotDialog")) return { ...React, useState: () => [page, () => {}] };
    if (name === "@/components/Button") return { default: "button" };
    if (name === "@/components/LoadingSkeleton") return { default: "div" };
    if (name === "@/components/Table") return load("src/components/Table.tsx");
    if (name === "@/utils/dateTime") return { formatFecha: (value: string) => value.split("-").reverse().join("/") };
    return require(name);
  } });
  return module.exports;
}

test("consulta de versión presenta exclusivamente los datos congelados de las tres clases", () => {
  const Dialog = load("src/modules/memorias/components/PersonalSnapshotDialog.tsx").default;
  for (const [sectionKey, label, field] of [
    ["personal", "Tipo de Personal", "tipo_personal_nombre"],
    ["becarios", "Nivel de Formación", "tipo_formacion_nombre"],
    ["investigadores", "Tipo de Dedicación", "tipo_dedicacion_nombre"],
  ]) {
    const html = renderToStaticMarkup(React.createElement(Dialog, { sectionKey, title: "Personal histórico", versionLabel: "Versión 1", onClose() {},
      items: [{ id: 1, nombre_apellido: "Nombre histórico", [field]: "Clasificación histórica", horas_semanales: 12, fecha_alta_grupo: "2020-03-01", grupo_utn_nombre: "Grupo histórico" }],
    }));
    for (const text of ["Nombre histórico", "Clasificación histórica", "Grupo histórico", "12 h", "01/03/2020", label, "Versión 1"]) assert.ok(html.includes(text), text);
    assert.match(html, /<dialog[^>]*aria-labelledby=/);
    assert.match(html, /Los cambios posteriores del integrante no modifican esta información/);
    assert.doesNotMatch(html, /href=|Editar|Reactivar|Dar de baja/);
  }
});

test("consulta histórica pagina a nueve y no completa datos ausentes con valores actuales", () => {
  const items = Array.from({ length: 11 }, (_, id) => ({ id, nombre_apellido: `Histórico ${id}` }));
  for (const page of [1, 2]) {
    const Dialog = load("src/modules/memorias/components/PersonalSnapshotDialog.tsx", page).default;
    const html = renderToStaticMarkup(React.createElement(Dialog, { sectionKey: "becarios", title: "Becarios", versionLabel: "Versión 2", items, onClose() {} }));
    assert.match(html, /Sin dato/);
    assert.equal((html.match(/Histórico /g) || []).length, page === 1 ? 9 : 2);
    assert.equal(html.includes("Histórico 10"), page === 2);
  }
});
