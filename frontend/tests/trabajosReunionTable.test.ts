import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  formatTrabajoReunionContractValue,
  formatTrabajoReunionAuthorHistoryEntry,
  formatTrabajoReunionHistoryEntry,
  isVisibleTrabajoReunionHistoryItem,
  presentTrabajoReunionHistoryItems,
} from "../src/modules/produccion/utils/trabajoReunionHistory.ts";

const homePath = "src/modules/produccion/pages/TrabajosReunionHome.tsx";

test("Trabajos en reuniones usa la grilla visual común", () => {
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
  assert.match(home, /getHistorialTrabajoReunionById/);
  assert.match(home, /renderExpanded=\{renderHistory\}/);
  assert.doesNotMatch(home, /<Tarjeta/);
});

test("la grilla conserva permisos, baja individual y reintentos", () => {
  const home = readFileSync(homePath, "utf8");
  assert.match(home, /activo && canEditRecords\(\)/);
  assert.match(home, /activo && canDeleteRecords\(\)/);
  assert.match(home, /await deleteTrabajoReunion\(pendingDelete\.id\)/);
  assert.match(home, /onRetry=\{\(\) => trabajos\.refetch\(\)\}/);
  assert.match(home, /navigate\(`\/trabajos-reunion\/\$\{trabajo\.id\}`/);
  assert.doesNotMatch(home, /selectMode/);
  assert.doesNotMatch(home, /showFilters/);
});

test("el historial omite acciones, inicializaciones y valores sin cambios", () => {
  assert.equal(isVisibleTrabajoReunionHistoryItem({ id: 1, campo: "accion", valor_anterior: "editar", valor_nuevo: "eliminar" }), false);
  assert.equal(isVisibleTrabajoReunionHistoryItem({ id: 2, campo: "tipo_reunion_id", valor_anterior: null, valor_nuevo: 4 }), false);
  assert.equal(isVisibleTrabajoReunionHistoryItem({ id: 3, campo: "titulo_trabajo", valor_anterior: "Trabajo A", valor_nuevo: "Trabajo A" }), false);
  assert.equal(isVisibleTrabajoReunionHistoryItem({ id: 4, campo: "titulo_trabajo", valor_anterior: "Trabajo A", valor_nuevo: "Trabajo B" }), true);
});

test("los eventos de autores son legibles aunque su valor anterior sea vacío", () => {
  const item = { id: 1, campo: "autores", valor_anterior: null, valor_nuevo: { accion: "vincular", detalle: { nombre_apellido: "Ada Lovelace", tipo: "Investigadora" } } };
  assert.equal(isVisibleTrabajoReunionHistoryItem(item), true);
  assert.deepEqual(formatTrabajoReunionHistoryEntry(item), { title: "Autor vinculado", description: "Ada Lovelace (Investigadora)" });

  const unlinkItem = { id: 2, campo: "autores", valor_anterior: null, valor_nuevo: { accion: "desvincular", detalle: { nombre_apellido: "Ana Pérez", tipo: "Investigador" } } };
  assert.deepEqual(formatTrabajoReunionAuthorHistoryEntry(unlinkItem), {
    title: "Autor desvinculado",
    description: "Ana Pérez (Investigador)",
  });
  assert.equal(formatTrabajoReunionAuthorHistoryEntry({ id: 3, campo: "procedencia", valor_anterior: "Córdoba", valor_nuevo: "Rosario" }), null);
});

test("las relaciones y objetos nunca producen object Object", () => {
  const catalogChange = formatTrabajoReunionHistoryEntry({ id: 1, campo: "tipo_reunion_id", valor_anterior: { nombre: "Congreso" }, valor_nuevo: { nombre: "Jornada" } });
  const unknownChange = formatTrabajoReunionHistoryEntry({ id: 2, campo: "grupo_utn_id", valor_anterior: { id: 1 }, valor_nuevo: { id: 2 } });
  assert.equal(catalogChange.description, "Congreso → Jornada");
  assert.equal(unknownChange.description, "Dato actualizado → Dato actualizado");
  assert.doesNotMatch(catalogChange.description, /\[object Object\]/);
  assert.doesNotMatch(unknownChange.description, /\[object Object\]/);
  assert.equal(formatTrabajoReunionContractValue({ nombre: "Congreso" }), "Congreso");
  assert.equal(formatTrabajoReunionContractValue({ id: 3 }), "");
  assert.equal(presentTrabajoReunionHistoryItems([{ id: 3, campo: "acciones", valor_anterior: "a", valor_nuevo: "b" }, { id: 4, campo: "procedencia", valor_anterior: "Córdoba", valor_nuevo: "Rosario" }]).length, 1);
});
