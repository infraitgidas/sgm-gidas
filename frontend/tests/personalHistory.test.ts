import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import { formatPersonalHistoryEntry } from "../src/modules/personal/utils/personalHistory.ts";

test("presenta la vinculacion de una beca sin exponer el JSON de auditoria", () => {
  const result = formatPersonalHistoryEntry({
    id: 1,
    campo: "becas",
    valor_anterior: null,
    valor_nuevo: {
      accion: "vincular",
      detalle: { beca_id: 5, fecha_inicio: "2023-02-01", fecha_fin: null, monto_percibido: 70000 },
    },
  });

  assert.equal(result.title, "Beca vinculada");
  assert.match(result.description, /Beca #5/);
  assert.match(result.description, /Inicio: 01\/02\/2023/);
  assert.match(result.description, /Sin fecha de fin/);
  assert.match(result.description, /Monto: ARS 70\.000/);
  assert.doesNotMatch(result.description, /accion|detalle|\{|\}/);
});

test("presenta actualizacion, desvinculacion y cambios de campo", () => {
  assert.equal(formatPersonalHistoryEntry({ id: 2, campo: "becas", valor_nuevo: { accion: "desvincular", detalle: { beca_id: 7 } } }).title, "Beca desvinculada");
  assert.equal(formatPersonalHistoryEntry({ id: 3, campo: "becas", valor_nuevo: { accion: "actualizar", detalle: { beca_id: 7 } } }).title, "Beca actualizada");
  assert.deepEqual(formatPersonalHistoryEntry({ id: 4, campo: "horas_semanales", valor_anterior: 10, valor_nuevo: 20 }), {
    title: "Horas semanales",
    description: "10 → 20",
  });
});

test("interpreta eventos históricos serializados como JSON sin mostrar su estructura", () => {
  const event = {accion: "actualizar", detalle: {beca_id: 5, fecha_fin: "2027-03-01", monto_percibido: 0}};
  for (const value of [JSON.stringify(event), JSON.stringify(JSON.stringify(event))]) {
    const result = formatPersonalHistoryEntry({id: 5, campo: "becas", valor_nuevo: value});
    assert.equal(result.title, "Beca actualizada");
    assert.match(result.description, /Fin: 01\/03\/2027/);
    assert.match(result.description, /Monto: ARS 0/);
    assert.doesNotMatch(result.description, /accion|detalle|beca_id|fecha_fin|\{|\}/);
  }
});

test("formatos inesperados de becas no rompen el historial ni exponen valores técnicos", () => {
  const unexpected = [
    {accion: "desconocida", detalle: {secreto_interno: "NO MOSTRAR"}},
    {accion: "actualizar", detalle: "NO MOSTRAR"},
    ["NO MOSTRAR"], "{JSON incompleto NO MOSTRAR", "NO MOSTRAR", null, 42,
  ];
  for (const value of unexpected) {
    const result = formatPersonalHistoryEntry({id: 6, campo: "becas", valor_anterior: value, valor_nuevo: value});
    assert.equal(result.title, "Becas actualizadas");
    assert.equal(result.description, "Se registró un cambio en las becas asignadas.");
  }
});

test("resume estados anteriores y nuevos de monto y fecha, incluyendo colecciones históricas", () => {
  const before = [{beca_id: 1, fecha_fin: "2026-12-01", monto_percibido: "1000.50"}];
  const after = [{beca_id: 1, fecha_fin: "2027-02-01", monto_percibido: "2000"}];
  const result = formatPersonalHistoryEntry({id: 7, campo: "becas", valor_anterior: JSON.stringify(before), valor_nuevo: after});
  assert.match(result.description, /Fin: 01\/12\/2026.*Monto: ARS 1\.000,5.*→.*Fin: 01\/02\/2027.*Monto: ARS 2\.000/);
  assert.equal(formatPersonalHistoryEntry({id: 8, campo: "becas", valor_anterior: after, valor_nuevo: []}).description,
    "Beca #1 · Fin: 01/02/2027 · Monto: ARS 2.000 → Sin becas asignadas");
});

test("solo presenta datos reconocidos y fechas válidas en eventos de beca", () => {
  const result = formatPersonalHistoryEntry({id: 9, campo: "becas", valor_nuevo: {
    accion: "actualizar", detalle: JSON.stringify({beca_id: 1, fecha_inicio: "2026-02-31", fecha_fin: "NO MOSTRAR",
      monto_percibido: "NO MOSTRAR", dato_interno: "NO MOSTRAR"}),
  }});
  assert.deepEqual(result, {title: "Beca actualizada", description: "Beca #1"});
  assert.deepEqual(formatPersonalHistoryEntry({id: 10, campo: "becas", valor_nuevo: {
    accion: "actualizar", detalle: {nombre_beca: "Beca doctoral", monto_percibido: null, fecha_fin: null},
  }}), {title: "Beca actualizada", description: "Beca doctoral · Sin fecha de fin · Monto: sin registrar"});
});

test("tarjeta real pagina historiales actuales e históricos sin imprimir JSON crudo", () => {
  const require = createRequire(import.meta.url);
  const source = ts.transpileModule(readFileSync("src/components/HistorialCambiosCard.tsx", "utf8"), {
    compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX},
  }).outputText;
  const values = [
    {accion: "actualizar", detalle: {beca_id: 1, fecha_fin: "2027-03-01", monto_percibido: 1500}},
    JSON.stringify({accion: "actualizar", detalle: {beca_id: 1, monto_percibido: 0}}),
    {accion: "desvincular", detalle: {beca_id: 1}},
    "{JSON incompleto NO MOSTRAR",
    {estructura_desconocida: "NO MOSTRAR"},
  ];
  for (const page of [1, 2]) {
    let stateIndex = 0;
    const module = {exports: {} as any};
    runInNewContext(source, {module, exports: module.exports, require: (name: string) => {
      if (name === "react") return {...React, useState: () => [stateIndex++ === 0 ? true : page, () => {}]};
      if (name === "@/components/ui/collapsible") return Object.fromEntries(
        ["Collapsible", "CollapsibleTrigger", "CollapsibleContent"].map(key => [key, ({children}: any) => children]));
      if (name === "@/utils/dateTime") return {formatFechaHora: () => "05/11/2026 12:00:00"};
      if (name === "@/components/Button") return {default: ({children, onClick, ...props}: any) => React.createElement("button", props, children)};
      if (name === "@/components/LoadingSkeleton") return {default: () => null};
      return require(name);
    }});
    const html = renderToStaticMarkup(React.createElement(module.exports.default, {
      items: values.map((value, id) => ({id, campo: "becas", valor_nuevo: value})), formatItemPresentation: formatPersonalHistoryEntry,
    }));
    assert.doesNotMatch(html, /NO MOSTRAR|accion|detalle|beca_id|fecha_fin|\[object Object\]/);
    assert.equal((html.match(/Fecha:<\/span>/g) ?? []).length, page === 1 ? 3 : 2);
    assert.ok(html.includes(`Página ${page} de 2`));
    assert.ok(html.includes(page === 1 ? "Beca actualizada" : "Se registró un cambio en las becas asignadas."));
  }
});
