export const CARGOS_DIRECTIVOS = ["Director", "Vicedirector"] as const;

export type CargoDirectivo = (typeof CARGOS_DIRECTIVOS)[number];

export type DirectivoConCargo = {
  cargo?: string | null;
};

export function normalizarCargoDirectivo(cargo?: string | null): string {
  return cargo?.trim().toLocaleLowerCase("es") ?? "";
}

export function buscarDirectivoPorCargo<T extends DirectivoConCargo>(
  directivos: readonly T[],
  cargo: CargoDirectivo
): T | undefined {
  const cargoNormalizado = normalizarCargoDirectivo(cargo);

  return directivos.find(
    (directivo) =>
      normalizarCargoDirectivo(directivo.cargo) === cargoNormalizado
  );
}

export function obtenerCargosDirectivosFaltantes(
  directivos: readonly DirectivoConCargo[]
): CargoDirectivo[] {
  return CARGOS_DIRECTIVOS.filter(
    (cargo) => !buscarDirectivoPorCargo(directivos, cargo)
  );
}
