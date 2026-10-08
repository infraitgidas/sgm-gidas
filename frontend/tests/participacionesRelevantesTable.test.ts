import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  formatParticipacionHistoryEntry,
  isVisibleParticipacionHistoryItem,
} from "../src/modules/proyectos/utils/participacionHistory.ts";
import {
  filtrarParticipantes,
  participanteClave,
  type ParticipanteBuscable,
} from "../src/modules/proyectos/utils/participanteSearch.ts";

const home = readFileSync("src/modules/proyectos/pages/ParticipacionesHome.tsx", "utf8");
const form = readFileSync("src/modules/proyectos/pages/ParticipacionesForm.tsx", "utf8");
const detail = readFileSync("src/modules/proyectos/pages/ParticipacionesDetalle.tsx", "utf8");
const service = readFileSync("src/modules/proyectos/services/participacionesServices.ts", "utf8");
const participanteField = readFileSync("src/modules/proyectos/components/ParticipanteField.tsx", "utf8");

test("Participaciones relevantes usa la tabla común y paginación aprobada", () => {
  assert.match(home, /<Table/);
  assert.match(home, /<TableSearch/);
  assert.match(home, /<TableFilterChip/);
  assert.match(home, /<TableFilterSelect/);
  assert.match(home, /const ITEMS_PER_PAGE = 9/);
  assert.match(home, /const HISTORY_PER_PAGE = 3/);
  assert.match(home, /density="compact"/);
  assert.match(home, /renderExpanded=\{renderHistory\}/);
  assert.doesNotMatch(home, /selectMode/);
  assert.doesNotMatch(home, /showFilters/);
});

test("la tabla conserva acciones individuales, permisos y reintentos", () => {
  assert.match(home, /TableRowActionButton action="view"/);
  assert.match(home, /active && canEditRecords\(\)/);
  assert.match(home, /active && canDeleteRecords\(\)/);
  assert.match(home, /await participaciones\.remove\(pendingDelete\.id\)/);
  assert.match(home, /onRetry=\{\(\) => participaciones\.refetch\(\)\}/);
  assert.match(home, /history\.refetch\(\)/);
});

test("formulario y contrato distinguen investigadores y becarios por rol e ID", () => {
  assert.match(service, /type ParticipanteRol = "investigador" \| "becario"/);
  assert.match(service, /participante: ParticipanteRef/);
  assert.match(form, /<ParticipanteField/);
  assert.match(form, /rol: "investigador"/);
  assert.match(form, /rol: "becario"/);
  assert.match(participanteField, /Buscar participante/);
  assert.match(participanteField, /Nombre, apellido o iniciales/);
  assert.match(participanteField, /Investigadores y becarios/);
  assert.match(participanteField, /RESULTADOS_POR_PAGINA = 5/);
  assert.match(form, /changed\.participante = participante/);
});

test("el buscador de participantes filtra por texto, iniciales y categoría", () => {
  const participantes: ParticipanteBuscable[] = [
    { rol: "investigador", id: 1, nombre_apellido: "María Pérez", tipo: "Investigador" },
    { rol: "becario", id: 1, nombre_apellido: "Martín Pereyra", tipo: "Becario" },
    { rol: "becario", id: 2, nombre_apellido: "Lucía Díaz", tipo: "Becario" },
  ];

  assert.deepEqual(
    filtrarParticipantes(participantes, "maria per", "").map(participanteClave),
    ["investigador:1"]
  );
  assert.deepEqual(
    filtrarParticipantes(participantes, "mp", "becario").map(participanteClave),
    ["becario:1"]
  );
  assert.deepEqual(
    filtrarParticipantes(participantes, "", "becario", participantes[1]).map(participanteClave),
    ["becario:2"]
  );
});

test("el historial omite acciones, inicializaciones y valores equivalentes", () => {
  assert.equal(isVisibleParticipacionHistoryItem({ id: 1, campo: "accion", valor_anterior: "a", valor_nuevo: "b" }), false);
  assert.equal(isVisibleParticipacionHistoryItem({ id: 2, campo: "participante", valor_anterior: null, valor_nuevo: { rol: "becario", id: 1 } }), false);
  assert.equal(isVisibleParticipacionHistoryItem({ id: 3, campo: "fecha", valor_anterior: "2025-01-01", valor_nuevo: "2025-01-01" }), false);
  assert.equal(isVisibleParticipacionHistoryItem({ id: 4, campo: "fecha", valor_anterior: "2025-01-01", valor_nuevo: "2025-02-01" }), true);
});

test("el historial muestra participante y fechas sin exponer IDs ni JSON", () => {
  assert.deepEqual(
    formatParticipacionHistoryEntry({
      id: 1,
      campo: "participante",
      valor_anterior: { rol: "investigador", id: 7, nombre_apellido: "Ana Pérez" },
      valor_nuevo: { rol: "becario", id: 7, nombre_apellido: "Luis Díaz" },
    }),
    { title: "Participante", description: "Ana Pérez (Investigador) → Luis Díaz (Becario)" }
  );
  assert.deepEqual(
    formatParticipacionHistoryEntry({ id: 2, campo: "fecha", valor_anterior: "2025-01-02", valor_nuevo: "2025-03-04" }),
    { title: "Fecha", description: "02/01/2025 → 04/03/2025" }
  );
  assert.match(detail, /presentParticipacionHistoryItems/);
  assert.match(detail, /history\.refetch\(\)/);
});
