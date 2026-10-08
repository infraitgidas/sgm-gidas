import assert from "node:assert/strict";
import test from "node:test";
import { formatDocumentacionHistoryEntry, presentDocumentacionHistoryItems } from "../src/modules/produccion/utils/documentacionHistory.ts";

test("El historial omite inicializaciones y presenta autores sin IDs", () => {
  const event = { id: 1, campo: "autores", valor_anterior: null, valor_nuevo: { accion: "desvincular", detalle: { nombre_apellido: "Ana Pérez" } } };
  assert.deepEqual(formatDocumentacionHistoryEntry(event), { title: "Autor desvinculado", description: "Ana Pérez" });
  assert.deepEqual(presentDocumentacionHistoryItems([
    { id: 2, campo: "accion", valor_anterior: "a", valor_nuevo: "b" },
    { id: 3, campo: "titulo", valor_anterior: null, valor_nuevo: "Inicial" },
    { id: 4, campo: "titulo", valor_anterior: "Igual", valor_nuevo: "Igual" },
    { id: 6, campo: "nombre_apellido", valor_anterior: "Ana Pérez", valor_nuevo: "Ana María Pérez" },
    { id: 7, campo: "autores", valor_anterior: null, valor_nuevo: { accion: "editar", detalle: { nombre_apellido: "Ana María Pérez" } } },
    event,
  ]), [event]);
  assert.equal(formatDocumentacionHistoryEntry({ id: 5, campo: "editorial", valor_anterior: { nombre: "A" }, valor_nuevo: { nombre: "B" } }).description, "A → B");
});
