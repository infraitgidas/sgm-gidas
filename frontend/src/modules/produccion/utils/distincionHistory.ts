import type { HistorialDistincionItem } from "@/modules/produccion/services/distincionesServices";

const HIDDEN_FIELDS = new Set(["accion", "acciones"]);

const FIELD_LABELS: Record<string, string> = {
  fecha: "Fecha",
  descripcion: "Descripción",
  proyecto_investigacion_id: "Proyecto de investigación",
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

export function isVisibleDistincionHistoryItem(item: HistorialDistincionItem) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  if (!field || HIDDEN_FIELDS.has(field)) return false;
  if (areEquivalentHistoryValues(item.valor_anterior, item.valor_nuevo)) return false;
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
  const code = typeof value.codigo === "string" ? value.codigo.trim() : "";
  const nameKeys = ["nombre", "nombre_proyecto", "nombre_sigla_grupo", "descripcion"];
  const name = nameKeys
    .map((key) => value[key])
    .find((candidate) => typeof candidate === "string" && candidate.trim());
  const normalizedName = typeof name === "string" ? name.trim() : "";
  if (code && normalizedName) return `${code} - ${normalizedName}`;
  return normalizedName || code;
}

function formatHistoryValue(
  value: unknown,
  field: string,
  projectNames: Record<number, string>
) {
  if (isEmptyHistoryValue(value)) return "Sin dato";
  if (field === "fecha") return formatDate(value);
  if (field === "proyecto_investigacion_id") {
    return projectNames[Number(value)] ?? "Proyecto actualizado";
  }
  if (typeof value === "object" && value !== null) {
    return formatObjectValue(value as Record<string, unknown>) || "Dato actualizado";
  }
  return String(value);
}

export function formatDistincionHistoryEntry(
  item: HistorialDistincionItem,
  projectNames: Record<number, string> = {}
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
      projectNames
    )} → ${formatHistoryValue(item.valor_nuevo, normalizedField, projectNames)}`,
  };
}

export function presentDistincionHistoryItems(items: HistorialDistincionItem[]) {
  return items.filter(isVisibleDistincionHistoryItem);
}
