import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  getActividadDocenciaHistoryCatalogName,
  isVisibleActividadDocenciaHistoryItem,
  presentActividadDocenciaHistoryItems,
} from "../src/modules/produccion/utils/actividadDocenciaHistory.ts";

test("Actividades en Docencia usa la grilla comun y acciones por fila", () => {
  const home = readFileSync("src/modules/produccion/pages/DocenciaHome.tsx", "utf8");

  assert.match(home, /<Table/);
  assert.match(home, /<TableSearch label="Buscar actividades en docencia"/);
  assert.match(home, /<TableFilterChip[^>]+active=\{activeFilter === "true"\}/);
  assert.match(home, /<TableRowActionButton action="view"/);
  assert.match(home, /<TableRowActionButton action="edit"/);
  assert.match(home, /<TableRowActionButton action="delete"/);
  assert.match(home, /getHistorialActividadDocenciaById/);
  assert.match(home, /const HISTORY_PER_PAGE = 3/);
  assert.doesNotMatch(home, /<Tarjeta/);
  assert.doesNotMatch(home, /selectMode/);
});

test("las acciones de Docencia conservan permisos, rutas y baja logica", () => {
  const home = readFileSync("src/modules/produccion/pages/DocenciaHome.tsx", "utf8");

  assert.match(home, /!item\.deleted_at && canEditRecords\(\)/);
  assert.match(home, /!item\.deleted_at && canDeleteRecords\(\)/);
  assert.match(home, /navigate\(`\/docenciaInvestigador\/\$\{item\.id\}\/editar`\)/);
  assert.match(home, /await eliminarActividadDocencia\(pendingDelete\.id\)/);
  assert.match(home, /getErrorMessage\(error, "Lo sentimos, no pudimos completar la operación\. Intente nuevamente\."\)/);
});

test("el historial de Docencia no presenta campos de acciones", () => {
  assert.equal(isVisibleActividadDocenciaHistoryItem({ id: 1, campo: "curso" }), true);
  assert.equal(isVisibleActividadDocenciaHistoryItem({ id: 2, campo: "accion" }), false);
  assert.equal(isVisibleActividadDocenciaHistoryItem({ id: 3, campo: " Acciones " }), false);

  const home = readFileSync("src/modules/produccion/pages/DocenciaHome.tsx", "utf8");
  const detail = readFileSync("src/modules/produccion/pages/DocenciaDetalle.tsx", "utf8");
  assert.match(home, /filter\(isVisibleActividadDocenciaHistoryItem\)/);
  assert.match(detail, /items=\{presentActividadDocenciaHistoryItems\(historialCambios\)\}/);
});

test("el detalle presenta cambios reales de grado con nombres legibles", () => {
  const items = presentActividadDocenciaHistoryItems([
    {
      id: 1,
      tipo: "historial_grado",
      campo: "grado_academico_id",
      valor_anterior: { id: 7, nombre: "Asistente" },
      valor_nuevo: { id: 8, nombre: "Titular" },
    },
  ]);

  assert.equal(items[0]?.tipo, "cambio_grado");
  assert.equal(items[0]?.campo, "grado académico");
  assert.equal(getActividadDocenciaHistoryCatalogName(items[0]?.valor_anterior), "Asistente");
  assert.equal(getActividadDocenciaHistoryCatalogName(items[0]?.valor_nuevo), "Titular");
});

test("Docencia normaliza Rol y Grado y usa un scrollbar compacto", () => {
  const service = readFileSync("src/modules/produccion/services/actividadDocenciaServices.ts", "utf8");
  const home = readFileSync("src/modules/produccion/pages/DocenciaHome.tsx", "utf8");

  assert.match(service, /grado_academico\?: string \| \{ id: number; nombre: string \} \| null/);
  assert.match(service, /rol_actividad\?: string \| \{ id: number; nombre: string \} \| null/);
  assert.match(service, /grado_academico: getNombreCatalogo\(item\.grado_academico\)/);
  assert.match(service, /rol_actividad: getNombreCatalogo\(item\.rol_actividad\)/);
  assert.match(home, /\[scrollbar-width:thin\]/);
  assert.match(home, /\[&::-webkit-scrollbar\]:h-1/);
  assert.match(home, /overflow-x-auto py-1 whitespace-nowrap/);
});
