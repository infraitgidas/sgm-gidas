export type AlcanceTrabajo = "nacional" | "internacional";

export function referatoLabel(value: unknown): string {
  return value === true ? "Sí" : value === false ? "No" : "Sin informar";
}

export function alcanceLabel(value: unknown): string {
  return value === "nacional" ? "Nacional" : value === "internacional" ? "Internacional" : "Sin informar";
}

export function procedenciaLabel(value: unknown): string {
  return value === "nacional" ? "Ciudad" : value === "internacional" ? "País" : "Procedencia";
}

export function referatoValue(value: string): boolean | null {
  return value === "true" ? true : value === "false" ? false : null;
}
