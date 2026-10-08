import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  formatArticuloHistoryEntry,
  isVisibleArticuloHistoryItem,
  presentArticuloHistoryItems,
} from "../src/modules/produccion/utils/articuloDivulgacionHistory.ts";

const homePath = "src/modules/produccion/pages/ArticulosDivulgacionHome.tsx";
const detailPath = "src/modules/produccion/pages/ArticulosDivulgacionDetalle.tsx";
const formPath = "src/modules/produccion/pages/ArticulosDivulgacionForm.tsx";

test("Artículos de divulgación usa la grilla visual común", () => {
  const home = readFileSync(homePath, "utf8");
  assert.match(home, /<Table/);
  assert.match(home, /<TableSearch/);
  assert.match(home, /<TableFilterChip/);
  assert.match(home, /<TableFilterSelect/);
  assert.match(home, /<TableRowActionButton action="view"/);
  assert.match(home, /<TableRowActionButton action="edit"/);
  assert.match(home, /<TableRowActionButton action="delete"/);
  assert.match(home, /density="compact"/);
  assert.match(home, /overflow-x-auto py-1 whitespace-nowrap/);
  assert.match(home, /\[scrollbar-width:thin\]/);
  assert.match(home, /const ITEMS_PER_PAGE = 9/);
  assert.match(home, /const HISTORY_PER_PAGE = 3/);
  assert.match(home, /getHistorialArticuloById/);
  assert.match(home, /renderExpanded=\{renderHistory\}/);
  assert.doesNotMatch(home, /<Tarjeta/);
});

test("la grilla conserva permisos, baja individual y reintentos", () => {
  const home = readFileSync(homePath, "utf8");
  assert.match(home, /activo && canEditRecords\(\)/);
  assert.match(home, /activo && canDeleteRecords\(\)/);
  assert.match(home, /await articulos\.remove\(pendingDelete\.id\)/);
  assert.match(home, /onRetry=\{\(\) => articulos\.refetch\(\)\}/);
  assert.match(home, /navigate\(`\/articulos-divulgacion\/\$\{item\.id\}`/);
  assert.doesNotMatch(home, /selectMode/);
  assert.doesNotMatch(home, /showFilters/);
});

test("el historial omite acciones, inicializaciones y valores equivalentes", () => {
  assert.equal(isVisibleArticuloHistoryItem({ id: 1, campo: "accion", valor_anterior: "editar", valor_nuevo: "eliminar" }), false);
  assert.equal(isVisibleArticuloHistoryItem({ id: 2, campo: "grupo_utn_id", valor_anterior: null, valor_nuevo: 4 }), false);
  assert.equal(isVisibleArticuloHistoryItem({ id: 3, campo: "titulo", valor_anterior: "Título", valor_nuevo: "Título" }), false);
  assert.equal(isVisibleArticuloHistoryItem({ id: 4, campo: "titulo", valor_anterior: "Título A", valor_nuevo: "Título B" }), true);
});

test("el historial presenta fechas y UCT con etiquetas legibles", () => {
  assert.deepEqual(
    formatArticuloHistoryEntry({ id: 1, campo: "fecha_publicacion", valor_anterior: "2025-01-02", valor_nuevo: "2025-03-04" }),
    { title: "Fecha de publicación", description: "02/01/2025 → 04/03/2025" }
  );
  assert.deepEqual(
    formatArticuloHistoryEntry({ id: 2, campo: "grupo_utn_id", valor_anterior: 1, valor_nuevo: 2 }, { 1: "UCT anterior", 2: "UCT actual" }),
    { title: "UCT", description: "UCT anterior → UCT actual" }
  );
  assert.equal(
    presentArticuloHistoryItems([
      { id: 3, campo: "acciones", valor_anterior: "a", valor_nuevo: "b" },
      { id: 4, campo: "descripcion", valor_anterior: "A", valor_nuevo: "B" },
    ]).length,
    1
  );
});

test("detalle y formulario mantienen historial seguro y errores accionables", () => {
  const detail = readFileSync(detailPath, "utf8");
  const form = readFileSync(formPath, "utf8");
  assert.match(detail, /presentArticuloHistoryItems/);
  assert.match(detail, /formatArticuloHistoryEntry/);
  assert.match(detail, /historial\.refetch\(\)/);
  assert.match(form, /initialQuery\.refetch\(\)/);
  assert.doesNotMatch(form, /errors\.titulo &&/);
  assert.doesNotMatch(form, /errors\.descripcion &&/);
});
