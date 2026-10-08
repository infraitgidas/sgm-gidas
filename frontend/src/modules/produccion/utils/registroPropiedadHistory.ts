import type { HistorialRegistroPropiedadItem } from "@/modules/produccion/services/registrosPropiedadServices";

const HIDDEN_FIELDS = new Set(["accion", "acciones"]);

const FIELD_LABELS: Record<string, string> = {
  nombre_articulo: "Nombre del artículo",
  organismo_registrante: "Organismo registrante",
  fecha_registro: "Fecha de registro",
  tipo_registro_id: "Tipo de registro",
  grupo_utn_id: "Grupo UTN",
};

export function formatRegistroPropiedadContractValue(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value !== "object") return String(value).trim();

  const record = value as Record<string, unknown>;
  for (const key of [
    "nombre",
    "nombre_sigla_grupo",
    "label",
    "descripcion",
    "detalle",
  ]) {
    const candidate = record[key];
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }

  return "";
}

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

export function isVisibleRegistroPropiedadHistoryItem(
  item: HistorialRegistroPropiedadItem
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

function formatHistoryValue(value: unknown, field?: string) {
  if (isEmptyHistoryValue(value)) return "Sin dato";
  if (field === "fecha_registro") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
    if (match) return `${match[3]}/${match[2]}/${match[1]}`;
  }
  if (typeof value === "object" && value !== null) {
    return formatRegistroPropiedadContractValue(value) || "Dato actualizado";
  }
  return String(value);
}

export function formatRegistroPropiedadHistoryEntry(
  item: HistorialRegistroPropiedadItem
) {
  const field = item.campo?.trim() ?? "";
  const title =
    FIELD_LABELS[field] ??
    field.replace(/_id$/, "").replace(/_/g, " ").replace(/^./, (letter) =>
      letter.toLocaleUpperCase("es")
    );

  return {
    title: title || "Cambio registrado",
    description: `${formatHistoryValue(item.valor_anterior, field)} → ${formatHistoryValue(item.valor_nuevo, field)}`,
  };
}

export function presentRegistroPropiedadHistoryItems(
  items: HistorialRegistroPropiedadItem[]
) {
  return items.filter(isVisibleRegistroPropiedadHistoryItem);
}
