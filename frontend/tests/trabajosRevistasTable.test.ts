import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  formatTrabajoRevistaContractValue,
  formatTrabajoRevistaAuthorHistoryEntry,
  formatTrabajoRevistaHistoryEntry,
  isVisibleTrabajoRevistaHistoryItem,
  presentTrabajoRevistaHistoryItems,
} from "../src/modules/produccion/utils/trabajoRevistaHistory.ts";

const homePath = "src/modules/produccion/pages/TrabajosRevistasHome.tsx";

test("Trabajos en revistas usa la grilla visual común", () => {
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
  assert.match(home, /\[&::\-webkit-scrollbar\]:h-1/);
  assert.match(home, /const ITEMS_PER_PAGE = 9/);
  assert.match(home, /const HISTORY_PER_PAGE = 3/);
  assert.match(home, /getHistorialTrabajoRevistaById/);
  assert.match(home, /renderExpanded=\{renderHistory\}/);
  assert.doesNotMatch(home, /<Tarjeta/);
});

test("la grilla usa el contrato y los textos propios de revistas", () => {
  const home = readFileSync(homePath, "utf8");
  assert.match(home, /tipo_revista/);
  assert.match(home, /fecha_publicacion/);
  assert.match(home, /Fecha de publicación/);
  assert.match(home, /Filtrar por tipo de revista/);
  assert.doesNotMatch(home, /tipo_reunion/);
  assert.doesNotMatch(home, /fecha_presentacion/);
});

test("la grilla conserva permisos, baja individual y reintentos", () => {
  const home = readFileSync(homePath, "utf8");
  assert.match(home, /activo && canEditRecords\(\)/);
  assert.match(home, /activo && canDeleteRecords\(\)/);
  assert.match(home, /await deleteTrabajoRevista\(pendingDelete\.id\)/);
  assert.match(home, /onRetry=\{\(\) => trabajos\.refetch\(\)\}/);
  assert.match(home, /navigate\(`\/trabajos-revistas\/\$\{trabajo\.id\}`/);
  assert.doesNotMatch(home, /selectMode/);
  assert.doesNotMatch(home, /showFilters/);
});

test("el historial omite acciones, inicializaciones y valores sin cambios", () => {
  assert.equal(isVisibleTrabajoRevistaHistoryItem({ id: 1, campo: "accion", valor_anterior: "editar", valor_nuevo: "eliminar" }), false);
  assert.equal(isVisibleTrabajoRevistaHistoryItem({ id: 2, campo: "tipo_revista_id", valor_anterior: null, valor_nuevo: 4 }), false);
  assert.equal(isVisibleTrabajoRevistaHistoryItem({ id: 3, campo: "titulo_trabajo", valor_anterior: "Trabajo A", valor_nuevo: "Trabajo A" }), false);
  assert.equal(isVisibleTrabajoRevistaHistoryItem({ id: 4, campo: "titulo_trabajo", valor_anterior: "Trabajo A", valor_nuevo: "Trabajo B" }), true);
});

test("el historial presenta fechas, catálogo y autores con etiquetas legibles", () => {
  assert.deepEqual(
    formatTrabajoRevistaHistoryEntry(
      { id: 1, campo: "fecha_publicacion", valor_anterior: "2025-01-02", valor_nuevo: "2025-03-04" }
    ),
    { title: "Fecha de publicación", description: "02/01/2025 → 04/03/2025" }
  );
  assert.deepEqual(
    formatTrabajoRevistaHistoryEntry(
      { id: 2, campo: "tipo_revista_id", valor_anterior: 1, valor_nuevo: 2 },
      { 1: "Nacional", 2: "Internacional" }
    ),
    { title: "Tipo de revista", description: "Nacional → Internacional" }
  );
  const authorItem = { id: 3, campo: "autores", valor_anterior: null, valor_nuevo: { accion: "desvincular", detalle: { nombre_apellido: "Ana Pérez", tipo: "Investigadora" } } };
  assert.deepEqual(formatTrabajoRevistaAuthorHistoryEntry(authorItem), {
    title: "Autor desvinculado",
    description: "Ana Pérez (Investigadora)",
  });
  assert.equal(isVisibleTrabajoRevistaHistoryItem(authorItem), true);
  assert.equal(formatTrabajoRevistaContractValue({ nombre: "Nacional" }), "Nacional");
  assert.equal(presentTrabajoRevistaHistoryItems([{ id: 4, campo: "acciones", valor_anterior: "a", valor_nuevo: "b" }, authorItem]).length, 1);
});
