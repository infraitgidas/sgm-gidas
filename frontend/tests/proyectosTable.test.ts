import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { formatProyectoHistoryEntry, formatProyectoRelationHistoryEntry } from "../src/modules/proyectos/utils/proyectoHistory.ts";

test("el historial de Proyectos presenta cambios y relaciones sin JSON", () => {
  assert.deepEqual(
    formatProyectoHistoryEntry({ id: 1, campo: "nombre_proyecto", valor_anterior: "Anterior", valor_nuevo: "Actual" }),
    { title: "Nombre del proyecto", description: "Anterior → Actual" }
  );
  assert.deepEqual(
    formatProyectoHistoryEntry({ id: 2, campo: "investigadores_ids", valor_nuevo: { accion: "vincular", detalle: { id: 7, nombre_apellido: "Ada Lovelace" } } }),
    { title: "Investigador vinculado", description: "Ada Lovelace" }
  );
  assert.deepEqual(
    formatProyectoRelationHistoryEntry(
      { id: 3, campo: "becarios_ids", valor_nuevo: { accion: "vincular", detalle: { id: 2 } } },
      { becarios: [{ id: 2, nombre_apellido: "Grace Hopper" }] }
    ),
    { title: "Becario vinculado", description: "Grace Hopper" }
  );
  assert.deepEqual(
    formatProyectoRelationHistoryEntry(
      { id: 4, campo: "coordinador_id", valor_anterior: null, valor_nuevo: 2 },
      { investigadores: [{ id: 2, nombre_apellido: "Dra. Ana Pérez" }] }
    ),
    { title: "Coordinador asignado", description: "Dra. Ana Pérez" }
  );
  assert.equal(formatProyectoRelationHistoryEntry({ id: 5, campo: "nombre_proyecto", valor_nuevo: "Proyecto" }), null);
});

test("Proyectos usa la tabla comun y nomenclatura de acciones consistente", () => {
  const home = readFileSync("src/modules/proyectos/pages/ProyectosHome.tsx", "utf8");
  const personalHome = readFileSync("src/modules/personal/pages/PersonalHome.tsx", "utf8");
  const field = readFileSync("src/modules/proyectos/components/PersonalProyectoField.tsx", "utf8");
  const table = readFileSync("src/components/Table.tsx", "utf8");
  const filterSelect = readFileSync("src/components/TableFilterSelect.tsx", "utf8");

  assert.match(home, /<Table/);
  assert.match(home, />Agregar nuevo<\/Button>/);
  assert.match(home, /<TableRowActionButton action="view"/);
  assert.match(home, /<TableRowActionButton action="edit"/);
  assert.match(home, /action="delete" label="Cerrar"/);
  assert.match(home, /action="restore" label="Reabrir"/);
  assert.match(home, /<TableFilterSelect label="Filtrar por tipo de proyecto"/);
  assert.doesNotMatch(home, /<select aria-label="Filtrar por tipo de proyecto"/);
  assert.match(table, /delete: \{ label: "Eliminar"/);
  assert.match(table, /<span>\{visibleLabel\}<\/span>/);
  assert.match(personalHome, /action="delete" label="Dar de baja"/);
  assert.doesNotMatch(personalHome, /title="Eliminar"/);
  assert.match(filterSelect, /import \{ Select \} from "radix-ui"/);
  assert.match(filterSelect, /Select\.Content/);
  assert.match(filterSelect, /data-\[highlighted\]:bg-slate-100/);
  assert.match(field, /type="search"/);
  assert.match(field, /const PAGE_SIZE = 5/);
  assert.match(field, /available\.slice\(availableStart, availableStart \+ PAGE_SIZE\)/);
  assert.match(field, /value\.slice\(selectedStart, selectedStart \+ PAGE_SIZE\)/);
  assert.match(field, />Siguiente<\/Button>/);
});
