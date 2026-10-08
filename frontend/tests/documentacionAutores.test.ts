import assert from "node:assert/strict";
import test from "node:test";
import { buscarAutoresDisponibles, normalizarNombreAutor } from "../src/modules/produccion/utils/documentacionAutores.ts";

const autores = [
  { id: 1, nombre_apellido: "Ana Pérez" },
  { id: 2, nombre_apellido: "Ada Lovelace" },
  { id: 3, nombre_apellido: "Juan Carlos Díaz" },
];

test("la búsqueda de autores acepta tildes, palabras e iniciales", () => {
  assert.deepEqual(buscarAutoresDisponibles(autores, [], "ana perez").map((autor) => autor.id), [1]);
  assert.deepEqual(buscarAutoresDisponibles(autores, [], "J.C.D.").map((autor) => autor.id), [3]);
  assert.deepEqual(buscarAutoresDisponibles(autores, [], "Lovelace").map((autor) => autor.id), [2]);
});

test("oculta los autores ya seleccionados por ID o nombre equivalente", () => {
  assert.deepEqual(buscarAutoresDisponibles(autores, [autores[0]], "").map((autor) => autor.id), [2, 3]);
  assert.deepEqual(buscarAutoresDisponibles(autores, [{ id: -1, nombre_apellido: "ANA  PEREZ" }], "").map((autor) => autor.id), [2, 3]);
  assert.equal(normalizarNombreAutor("  Ána   Pérez "), "ana perez");
});
