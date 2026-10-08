import assert from "node:assert/strict";
import test from "node:test";
import {
  buscarDirectivoPorCargo,
  normalizarCargoDirectivo,
  obtenerCargosDirectivosFaltantes,
} from "../src/modules/grupo/utils/directivoCargo.ts";

test("normaliza espacios y mayusculas de los cargos institucionales", () => {
  assert.equal(normalizarCargoDirectivo("  DIRECTOR "), "director");
  assert.equal(normalizarCargoDirectivo("ViceDirector"), "vicedirector");
});

test("identifica el directivo correspondiente sin depender del formato", () => {
  const directivos = [
    { nombre_apellido: "Ana", cargo: " director " },
    { nombre_apellido: "Bruno", cargo: "VICEDIRECTOR" },
  ];

  assert.equal(
    buscarDirectivoPorCargo(directivos, "Director")?.nombre_apellido,
    "Ana"
  );
  assert.equal(
    buscarDirectivoPorCargo(directivos, "Vicedirector")?.nombre_apellido,
    "Bruno"
  );
});

test("si existe un director solo permite completar el vicedirector", () => {
  assert.deepEqual(
    obtenerCargosDirectivosFaltantes([{ cargo: "Director" }]),
    ["Vicedirector"]
  );
});

test("no ofrece altas cuando ambos cargos ya estan activos", () => {
  assert.deepEqual(
    obtenerCargosDirectivosFaltantes([
      { cargo: "Director" },
      { cargo: "Vicedirector" },
    ]),
    []
  );
});
