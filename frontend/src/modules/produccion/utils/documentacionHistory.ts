import type { HistorialDocumentacionItem } from "@/modules/produccion/services/documentacionServices";

const labels: Record<string, string> = {
  titulo: "Título",
  editorial: "Editorial",
  anio: "Año",
  fecha: "Fecha",
  grupo_id: "Grupo",
};
const documentacionFields = new Set(Object.keys(labels));

function readable(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Sin dato";
  if (typeof value !== "object") return String(value);
  const record = value as Record<string, unknown>;
  for (const key of ["nombre_apellido", "nombre", "nombre_sigla_grupo", "label", "descripcion"]) {
    if (typeof record[key] === "string" && record[key].trim()) return record[key].trim();
  }
  return "Dato actualizado";
}

function authorEvent(item: HistorialDocumentacionItem) {
  if (item.campo !== "autores" || !item.valor_nuevo || typeof item.valor_nuevo !== "object") return null;
  const value = item.valor_nuevo as Record<string, unknown>;
  if (value.accion !== "vincular" && value.accion !== "desvincular") return null;
  const detail = value.detalle && typeof value.detalle === "object" ? value.detalle : value;
  return { title: value.accion === "desvincular" ? "Autor desvinculado" : "Autor vinculado", description: readable(detail) };
}

export function presentDocumentacionHistoryItems(items: HistorialDocumentacionItem[]) {
  return items.filter((item) => {
    const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
    if (!documentacionFields.has(field) && field !== "autores") return false;
    if (authorEvent(item)) return true;
    if (field === "autores") return false;
    if (Object.is(item.valor_anterior, item.valor_nuevo)) return false;
    if (item.valor_anterior == null || item.valor_anterior === "") return false;
    if (typeof item.valor_anterior === "object" && typeof item.valor_nuevo === "object" && JSON.stringify(item.valor_anterior) === JSON.stringify(item.valor_nuevo)) return false;
    return true;
  });
}

export function formatDocumentacionHistoryEntry(item: HistorialDocumentacionItem) {
  const event = authorEvent(item);
  if (event) return event;
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  return { title: labels[field] ?? "Cambio registrado", description: `${formatDocumentacionHistoryValue(item, item.valor_anterior)} → ${formatDocumentacionHistoryValue(item, item.valor_nuevo)}` };
}

export function formatDocumentacionHistoryValue(item: HistorialDocumentacionItem, value: unknown) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  if (field === "fecha" && typeof value === "string") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (match) return `${match[3]}/${match[2]}/${match[1]}`;
  }
  if (field === "grupo_id" && typeof value === "number") return "Grupo actualizado";
  return readable(value);
}

export function formatDocumentacionAuthorHistoryEntry(item: HistorialDocumentacionItem) {
  return authorEvent(item);
}
