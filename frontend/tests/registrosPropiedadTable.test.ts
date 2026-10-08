import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  formatRegistroPropiedadContractValue,
  formatRegistroPropiedadHistoryEntry,
  isVisibleRegistroPropiedadHistoryItem,
  presentRegistroPropiedadHistoryItems,
} from "../src/modules/produccion/utils/registroPropiedadHistory.ts";

const homePath =
  "src/modules/produccion/pages/RegistrosPropiedadHome.tsx";

test("Registros de propiedad usa la grilla visual comun", () => {
  const home = readFileSync(homePath, "utf8");

  assert.match(home, /<Table/);
  assert.match(home, /<TableSearch/);
  assert.match(home, /<TableFilterChip/);
  assert.match(home, /<TableFilterSelect/);
  assert.match(home, /<TableRowActionButton\s+action="view"/);
  assert.match(home, /<TableRowActionButton\s+action="edit"/);
  assert.match(home, /<TableRowActionButton\s+action="delete"/);
  assert.match(home, /density="compact"/);
  assert.match(home, /overflow-x-auto pb-1 whitespace-nowrap/);
  assert.match(home, /const ITEMS_PER_PAGE = 9/);
  assert.match(home, /const HISTORY_PER_PAGE = 3/);
  assert.match(home, /getHistorialRegistroPropiedadById/);
  assert.match(home, /renderExpanded=\{renderHistory\}/);
  assert.doesNotMatch(home, /<Tarjeta/);
});

test("la grilla usa filtros y acciones por fila consistentes", () => {
  const home = readFileSync(homePath, "utf8");

  assert.match(home, /!registro\.deleted_at && canEditRecords\(\)/);
  assert.match(home, /!registro\.deleted_at && canDeleteRecords\(\)/);
  assert.match(home, /await deleteRegistroPropiedad\(pendingDelete\.id\)/);
  assert.match(home, /navigate\(`\/registros-propiedad\/\$\{registro\.id\}`/);
  assert.match(home, /navigate\(`\/registros-propiedad\/\$\{registro\.id\}\/editar`\)/);
  assert.match(home, /queryKey: \["registros-propiedad"\]/);
  assert.doesNotMatch(home, /selectMode/);
  assert.doesNotMatch(home, /showFilters/);
});

test("el historial omite acciones, inicializaciones y valores sin cambios", () => {
  assert.equal(
    isVisibleRegistroPropiedadHistoryItem({
      id: 1,
      campo: "accion",
      valor_anterior: "editar",
      valor_nuevo: "eliminar",
    }),
    false
  );
  assert.equal(
    isVisibleRegistroPropiedadHistoryItem({
      id: 2,
      campo: " Acciones ",
      valor_anterior: null,
      valor_nuevo: "crear",
    }),
    false
  );
  assert.equal(
    isVisibleRegistroPropiedadHistoryItem({
      id: 3,
      campo: "tipo_registro_id",
      valor_anterior: null,
      valor_nuevo: 4,
    }),
    false
  );
  assert.equal(
    isVisibleRegistroPropiedadHistoryItem({
      id: 4,
      campo: "nombre_articulo",
      valor_anterior: "Patente A",
      valor_nuevo: "Patente A",
    }),
    false
  );
  assert.equal(
    isVisibleRegistroPropiedadHistoryItem({
      id: 5,
      campo: "nombre_articulo",
      valor_anterior: "Patente A",
      valor_nuevo: "Patente B",
    }),
    true
  );
});

test("el historial nunca presenta objetos como object Object", () => {
  const named = formatRegistroPropiedadHistoryEntry({
    id: 1,
    campo: "tipo_registro_id",
    valor_anterior: { nombre: "Patente" },
    valor_nuevo: { nombre: "Modelo de utilidad" },
  });
  const unknown = formatRegistroPropiedadHistoryEntry({
    id: 2,
    campo: "grupo_utn_id",
    valor_anterior: { id: 1 },
    valor_nuevo: { id: 2 },
  });

  assert.equal(named.description, "Patente → Modelo de utilidad");
  assert.equal(unknown.description, "Dato actualizado → Dato actualizado");
  assert.doesNotMatch(named.description, /\[object Object\]/);
  assert.doesNotMatch(unknown.description, /\[object Object\]/);
  assert.equal(
    presentRegistroPropiedadHistoryItems([
      { id: 3, campo: "acciones", valor_anterior: "a", valor_nuevo: "b" },
      {
        id: 4,
        campo: "organismo_registrante",
        valor_anterior: "INPI",
        valor_nuevo: "DNDA",
      },
    ]).length,
    1
  );

  const detail = readFileSync(
    "src/modules/produccion/pages/RegistrosPropiedadDetalle.tsx",
    "utf8"
  );
  assert.match(detail, /items=\{presentRegistroPropiedadHistoryItems\(historialCambios\)\}/);
});

test("las columnas normalizan relaciones sin mostrar object Object", () => {
  assert.equal(
    formatRegistroPropiedadContractValue({ nombre: "Patente" }),
    "Patente"
  );
  assert.equal(
    formatRegistroPropiedadContractValue({ nombre_sigla_grupo: "GIDAS" }),
    "GIDAS"
  );
  assert.equal(formatRegistroPropiedadContractValue({ id: 4 }), "");
  assert.doesNotMatch(
    formatRegistroPropiedadContractValue({ id: 4 }),
    /\[object Object\]/
  );
});
