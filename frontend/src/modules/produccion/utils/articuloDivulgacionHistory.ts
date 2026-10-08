import type { HistorialArticuloDivulgacionItem } from "@/modules/produccion/services/articulosDivulgacionServices";

const HIDDEN_FIELDS = new Set(["accion", "acciones"]);

const FIELD_LABELS: Record<string, string> = {
  titulo: "Título",
  descripcion: "Descripción",
  fecha_publicacion: "Fecha de publicación",
  grupo_utn_id: "UCT",
};

function isEmptyHistoryValue(value: unknown) {
  return value === null || value === undefined || value === "";
}

function areEquivalentHistoryValues(previous: unknown, next: unknown) {
  if (Object.is(previous, next)) return true;
  if (
    typeof previous === "object" &&
    previous !== null &&
    typeof next === "object" &&
    next !== null
  ) {
    return JSON.stringify(previous) === JSON.stringify(next);
  }
  return false;
}

export function isVisibleArticuloHistoryItem(
  item: HistorialArticuloDivulgacionItem
) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  if (!field || HIDDEN_FIELDS.has(field)) return false;
  if (areEquivalentHistoryValues(item.valor_anterior, item.valor_nuevo)) {
    return false;
  }
  return !(
    isEmptyHistoryValue(item.valor_anterior) &&
    !isEmptyHistoryValue(item.valor_nuevo)
  );
}

function formatDate(value: unknown) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value);
}

function formatObjectValue(value: Record<string, unknown>) {
  const nameKeys = ["nombre", "nombre_sigla_grupo", "descripcion", "titulo"];
  const name = nameKeys
    .map((key) => value[key])
    .find((candidate) => typeof candidate === "string" && candidate.trim());
  return typeof name === "string" ? name.trim() : "";
}

function formatHistoryValue(
  value: unknown,
  field: string,
  groupNames: Record<number, string>
) {
  if (isEmptyHistoryValue(value)) return "Sin dato";
  if (field === "fecha_publicacion") return formatDate(value);
  if (field === "grupo_utn_id") {
    return groupNames[Number(value)] ?? "UCT actualizada";
  }
  if (typeof value === "object" && value !== null) {
    return formatObjectValue(value as Record<string, unknown>) || "Dato actualizado";
  }
  return String(value);
}

export function formatArticuloHistoryEntry(
  item: HistorialArticuloDivulgacionItem,
  groupNames: Record<number, string> = {}
) {
  const field = item.campo?.trim() ?? "";
  const normalizedField = field.toLocaleLowerCase("es");
  const title =
    FIELD_LABELS[normalizedField] ??
    field
      .replace(/_id$/, "")
      .replace(/_/g, " ")
      .replace(/^./, (letter) => letter.toLocaleUpperCase("es"));

  return {
    title: title || "Cambio registrado",
    description: `${formatHistoryValue(
      item.valor_anterior,
      normalizedField,
      groupNames
    )} → ${formatHistoryValue(item.valor_nuevo, normalizedField, groupNames)}`,
  };
}

export function presentArticuloHistoryItems(
  items: HistorialArticuloDivulgacionItem[]
) {
  return items.filter(isVisibleArticuloHistoryItem);
}
