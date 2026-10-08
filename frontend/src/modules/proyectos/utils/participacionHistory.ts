import type { HistorialParticipacionItem } from "@/modules/proyectos/services/participacionesServices";

const HIDDEN_FIELDS = new Set(["accion", "acciones"]);
const LABELS: Record<string, string> = {
  nombre_evento: "Nombre del evento",
  forma_participacion: "Forma de participación",
  fecha: "Fecha",
  participante: "Participante",
  investigador_id: "Participante",
  becario_id: "Participante",
};

const empty = (value: unknown) => value === null || value === undefined || value === "";

export function isVisibleParticipacionHistoryItem(item: HistorialParticipacionItem) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  if (!field || HIDDEN_FIELDS.has(field)) return false;
  if (JSON.stringify(item.valor_anterior) === JSON.stringify(item.valor_nuevo)) return false;
  return !(empty(item.valor_anterior) && !empty(item.valor_nuevo));
}

function formatValue(value: unknown, field: string) {
  if (empty(value)) return "Sin dato";
  if (field === "fecha") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
    if (match) return `${match[3]}/${match[2]}/${match[1]}`;
  }
  if (field === "forma_participacion") {
    const labels: Record<string, string> = {
      jurado: "Jurado",
      evaluador: "Evaluador",
      panelista: "Panelista",
      comite: "Miembro de comité científico",
    };
    return labels[String(value)] ?? String(value);
  }
  if (typeof value === "object" && value !== null) {
    const object = value as Record<string, unknown>;
    const name = object.nombre_apellido ?? object.nombre ?? object.descripcion;
    const type = object.rol === "becario" ? "Becario" : object.rol === "investigador" ? "Investigador" : "";
    return typeof name === "string" && name.trim()
      ? `${name.trim()}${type ? ` (${type})` : ""}`
      : "Participante actualizado";
  }
  if (field.endsWith("_id")) return "Participante actualizado";
  return String(value);
}

export function formatParticipacionHistoryEntry(item: HistorialParticipacionItem) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  return {
    title: LABELS[field] ?? "Cambio registrado",
    description: `${formatValue(item.valor_anterior, field)} → ${formatValue(item.valor_nuevo, field)}`,
  };
}

export const presentParticipacionHistoryItems = (items: HistorialParticipacionItem[]) =>
  items.filter(isVisibleParticipacionHistoryItem);
