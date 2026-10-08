import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  formatVisitHistoryEntry,
  presentVisitHistoryItems,
} from "../src/modules/grupo/utils/visitHistory.ts";

const serviceSource = await readFile(
  new URL("../src/modules/grupo/services/tiposVisitaServices.ts", import.meta.url),
  "utf8"
);
const formSource = await readFile(
  new URL("../src/modules/grupo/pages/VisitantesForm.tsx", import.meta.url),
  "utf8"
);
const catalogsSource = await readFile(
  new URL("../src/modules/catalogos/pages/CatalogosHome.tsx", import.meta.url),
  "utf8"
);
const homeSource = await readFile(
  new URL("../src/modules/grupo/pages/VisitantesHome.tsx", import.meta.url),
  "utf8"
);

test("consulta el catalogo propio de tipos de visita", () => {
  assert.match(serviceSource, /"\/grupo\/tipos-visita\/"/);
  assert.doesNotMatch(serviceSource, /tipos-reunion-cientifica/);
});

test("distingue el tipo de visita de la procedencia en el formulario", () => {
  assert.match(formSource, /label="Tipo de visita"/);
  assert.match(formSource, /label="Procedencia u origen"/);
  assert.match(formSource, /Clasifique el propósito de la visita/);
  assert.match(formSource, /desde donde proviene la visita/);
});

test("incluye el tipo de visita en la administracion de catalogos", () => {
  assert.match(catalogsSource, /label: "Tipo de Visita"/);
  assert.match(catalogsSource, /endpoint: "\/grupo\/tipos-visita\/"/);
});

test("estandariza el home de visitas con tabla, filtros y acciones individuales", () => {
  assert.match(homeSource, /caption="Listado de visitas"/);
  assert.match(homeSource, /header: "Tipo de visita"/);
  assert.match(homeSource, /header: "Procedencia u origen"/);
  assert.match(homeSource, /TableFilterChip/);
  assert.match(homeSource, /TableFilterSelect/);
  assert.match(homeSource, /TableRowActionButton/);
  assert.match(homeSource, /getHistorialVisitanteById/);
  assert.match(homeSource, /<ul className="space-y-2">/);
  assert.match(homeSource, /rounded-lg border border-slate-200 bg-white p-3 text-sm/);
  assert.match(homeSource, /Por \{entry\.usuario_nombre\}/);
  assert.doesNotMatch(homeSource, /md:grid-cols-3/);
  assert.doesNotMatch(homeSource, /selectMode/);
  assert.doesNotMatch(homeSource, /showFilters/);
});

test("presenta el historial de visitas con valores funcionales y sin IDs internos", () => {
  const items = presentVisitHistoryItems([
    { id: 1, campo: "accion", valor_anterior: null, valor_nuevo: "editar" },
    { id: 2, campo: "razon", valor_anterior: null, valor_nuevo: "Visita inicial" },
    { id: 3, campo: "procedencia", valor_anterior: "Córdoba", valor_nuevo: "Mendoza" },
    { id: 4, campo: "procedencia", valor_anterior: "Mendoza", valor_nuevo: "Mendoza" },
  ]);

  assert.deepEqual(items.map((item) => item.id), [3]);

  const presentation = formatVisitHistoryEntry(
    {
      id: 5,
      campo: "tipo_visita_id",
      valor_anterior: 1,
      valor_nuevo: 2,
    },
    {
      tiposVisita: new Map([
        [1, "Académica"],
        [2, "Intercambio"],
      ]),
    }
  );

  assert.equal(presentation.title, "Tipo de visita");
  assert.match(presentation.description, /Académica/);
  assert.match(presentation.description, /Intercambio/);
  assert.match(presentation.description, /Académica → Intercambio/);
  assert.doesNotMatch(presentation.description, /ID\s+\d/);
});
