export type Moneda = "ARS" | "USD";

export function isMoneda(value: unknown): value is Moneda {
  return value === "ARS" || value === "USD";
}

export function formatImporte(value?: number | null, moneda: Moneda = "ARS") {
  return typeof value === "number" && Number.isFinite(value)
    ? new Intl.NumberFormat("es-AR", {
        style: "currency", currency: moneda, currencyDisplay: "code",
      }).format(value)
    : "-";
}

// El historial del importe no debe adoptar la moneda actual del registro.
// Los cambios de moneda se presentan en su propio evento de auditoría.
export function formatImporteHistorial(value: unknown) {
  const number = Number(value);
  return value !== null && value !== undefined && value !== "" && Number.isFinite(number)
    ? new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(number)
    : "-";
}
