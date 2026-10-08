import type { HistorialActividadDocenciaItem } from "@/modules/produccion/services/actividadDocenciaServices";

const hiddenHistoryFields = new Set(["accion", "acciones"]);

export function isVisibleActividadDocenciaHistoryItem(
  item: HistorialActividadDocenciaItem
) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  return !hiddenHistoryFields.has(field);
}

export function presentActividadDocenciaHistoryItems(
  items: HistorialActividadDocenciaItem[]
) {
  return items
    .filter(isVisibleActividadDocenciaHistoryItem)
    .map((item) => item.tipo === "historial_grado"
      ? { ...item, tipo: "cambio_grado", campo: "grado académico" }
      : item);
}

export function getActividadDocenciaHistoryCatalogName(value: unknown) {
  if (!value || typeof value !== "object") return null;
  const name = (value as { nombre?: unknown }).nombre;
  return typeof name === "string" && name.trim() ? name : null;
}
