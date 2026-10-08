import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  formatDistincionHistoryEntry,
  isVisibleDistincionHistoryItem,
  presentDistincionHistoryItems,
} from "../src/modules/produccion/utils/distincionHistory.ts";

const homePath = "src/modules/produccion/pages/DistincionesHome.tsx";
const detailPath = "src/modules/produccion/pages/DistincionesDetalle.tsx";

test("Distinciones recibidas usa la grilla visual común", () => {
  const home = readFileSync(homePath, "utf8");
  assert.match(home, /<Table/);
  assert.match(home, /<TableSearch/);
  assert.match(home, /<TableFilterChip/);
  assert.match(home, /<TableFilterSelect/);
  assert.match(home, /<TableRowActionButton\s+action="view"/);
  assert.match(home, /<TableRowActionButton\s+action="edit"/);
  assert.match(home, /<TableRowActionButton\s+action="delete"/);
  assert.match(home, /density="compact"/);
  assert.match(home, /overflow-x-auto py-1 whitespace-nowrap/);
  assert.match(home, /\[scrollbar-width:thin\]/);
  assert.match(home, /\[&::\-webkit-scrollbar\]:h-1/);
  assert.match(home, /const ITEMS_PER_PAGE = 9/);
  assert.match(home, /const HISTORY_PER_PAGE = 3/);
  assert.match(home, /getHistorialDistincionById/);
  assert.match(home, /renderExpanded=\{renderHistory\}/);
  assert.doesNotMatch(home, /<Tarjeta/);
});

test("la grilla conserva permisos, baja individual y reintentos", () => {
  const home = readFileSync(homePath, "utf8");
  assert.match(home, /activo && canEditRecords\(\)/);
  assert.match(home, /activo && canDeleteRecords\(\)/);
  assert.match(home, /await distinciones\.remove\(pendingDelete\.id\)/);
  assert.match(home, /onRetry=\{\(\) => distinciones\.refetch\(\)\}/);
  assert.match(home, /navigate\(`\/distinciones\/\$\{item\.id\}`/);
  assert.doesNotMatch(home, /selectMode/);
  assert.doesNotMatch(home, /showFilters/);
});

test("el historial omite acciones, inicializaciones y valores sin cambios", () => {
  assert.equal(
    isVisibleDistincionHistoryItem({
      id: 1,
      campo: "accion",
      valor_anterior: "editar",
      valor_nuevo: "eliminar",
    }),
    false
  );
  assert.equal(
    isVisibleDistincionHistoryItem({
      id: 2,
      campo: "proyecto_investigacion_id",
      valor_anterior: null,
      valor_nuevo: 4,
    }),
    false
  );
  assert.equal(
    isVisibleDistincionHistoryItem({
      id: 3,
      campo: "descripcion",
      valor_anterior: "Premio A",
      valor_nuevo: "Premio A",
    }),
    false
  );
  assert.equal(
    isVisibleDistincionHistoryItem({
      id: 4,
      campo: "descripcion",
      valor_anterior: "Premio A",
      valor_nuevo: "Premio B",
    }),
    true
  );
});

test("el historial presenta fechas y proyectos con etiquetas legibles", () => {
  assert.deepEqual(
    formatDistincionHistoryEntry({
      id: 1,
      campo: "fecha",
      valor_anterior: "2025-01-02",
      valor_nuevo: "2025-03-04",
    }),
    { title: "Fecha", description: "02/01/2025 → 04/03/2025" }
  );
  assert.deepEqual(
    formatDistincionHistoryEntry(
      {
        id: 2,
        campo: "proyecto_investigacion_id",
        valor_anterior: 1,
        valor_nuevo: 2,
      },
      { 1: "P-01 - Proyecto anterior", 2: "P-02 - Proyecto actual" }
    ),
    {
      title: "Proyecto de investigación",
      description: "P-01 - Proyecto anterior → P-02 - Proyecto actual",
    }
  );
  assert.equal(
    presentDistincionHistoryItems([
      { id: 3, campo: "acciones", valor_anterior: "a", valor_nuevo: "b" },
      { id: 4, campo: "descripcion", valor_anterior: "A", valor_nuevo: "B" },
    ]).length,
    1
  );
});

test("el detalle reutiliza la presentación segura del historial", () => {
  const detail = readFileSync(detailPath, "utf8");
  assert.match(detail, /presentDistincionHistoryItems/);
  assert.match(detail, /formatDistincionHistoryEntry/);
  assert.match(detail, /historial\.refetch\(\)/);
  assert.doesNotMatch(detail, /JSON\.stringify\(value\)/);
});
