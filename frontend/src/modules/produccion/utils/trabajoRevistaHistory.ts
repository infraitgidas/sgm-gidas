import type { HistorialTrabajoRevistaItem } from "@/modules/produccion/services/trabajosRevistasServices";

const HIDDEN_FIELDS = new Set(["accion", "acciones"]);
const FIELD_LABELS: Record<string, string> = {
  titulo_trabajo: "Título del trabajo",
  nombre_revista: "Nombre de la revista",
  editorial: "Editorial",
  issn: "ISSN",
  pais: "País",
  fecha_publicacion: "Fecha de publicación",
  tipo_revista_id: "Tipo de revista",
  grupo_utn_id: "UCT",
  enlace: "Enlace al trabajo o DOI",
};

export function formatTrabajoRevistaContractValue(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value !== "object") return String(value).trim();
  const record = value as Record<string, unknown>;
  for (const key of ["nombre", "nombre_apellido", "nombre_sigla_grupo", "label", "descripcion"]) {
    const candidate = record[key];
    if (typeof candidate === "string" && candidate.trim()) return candidate.trim();
  }
  return "";
}

function isEmptyHistoryValue(value: unknown) {
  return value === null || value === undefined || value === "";
}

function areEquivalentHistoryValues(previous: unknown, next: unknown) {
  if (Object.is(previous, next)) return true;
  if (typeof previous === "object" && previous !== null && typeof next === "object" && next !== null) {
    return JSON.stringify(previous) === JSON.stringify(next);
  }
  return false;
}

function getAutorEvent(item: HistorialTrabajoRevistaItem) {
  if (item.campo?.trim().toLocaleLowerCase("es") !== "autores") return null;
  const source = typeof item.valor_nuevo === "object" && item.valor_nuevo !== null
    ? item.valor_nuevo as Record<string, unknown>
    : null;
  if (!source) return null;
  const detalle = typeof source.detalle === "object" && source.detalle !== null
    ? source.detalle as Record<string, unknown>
    : source;
  return {
    action: typeof source.accion === "string" ? source.accion : "",
    name: formatTrabajoRevistaContractValue(detalle),
    type: typeof detalle.tipo === "string" ? detalle.tipo.trim() : "",
  };
}

export function isVisibleTrabajoRevistaHistoryItem(item: HistorialTrabajoRevistaItem) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  if (!field || HIDDEN_FIELDS.has(field)) return false;
  if (getAutorEvent(item)) return true;
  if (areEquivalentHistoryValues(item.valor_anterior, item.valor_nuevo)) return false;
  return !(isEmptyHistoryValue(item.valor_anterior) && !isEmptyHistoryValue(item.valor_nuevo));
}

function formatDate(value: unknown) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value);
}

function formatHistoryValue(value: unknown, field: string, tipoNames: Record<number, string>) {
  if (isEmptyHistoryValue(value)) return "Sin dato";
  if (field === "fecha_publicacion") return formatDate(value);
  if (field === "tipo_revista_id") {
    const name = tipoNames[Number(value)] ?? formatTrabajoRevistaContractValue(value);
    return name || "Dato actualizado";
  }
  if (typeof value === "object") return formatTrabajoRevistaContractValue(value) || "Dato actualizado";
  return String(value);
}

export function formatTrabajoRevistaHistoryEntry(
  item: HistorialTrabajoRevistaItem,
  tipoNames: Record<number, string> = {}
) {
  const authorPresentation = formatTrabajoRevistaAuthorHistoryEntry(item);
  if (authorPresentation) return authorPresentation;
  const field = item.campo?.trim() ?? "";
  const normalizedField = field.toLocaleLowerCase("es");
  const title = FIELD_LABELS[normalizedField]
    ?? field.replace(/_id$/, "").replace(/_/g, " ").replace(/^./, (letter) => letter.toLocaleUpperCase("es"));
  return {
    title: title || "Cambio registrado",
    description: `${formatHistoryValue(item.valor_anterior, normalizedField, tipoNames)} → ${formatHistoryValue(item.valor_nuevo, normalizedField, tipoNames)}`,
  };
}

export function formatTrabajoRevistaAuthorHistoryEntry(item: HistorialTrabajoRevistaItem) {
  const autorEvent = getAutorEvent(item);
  if (!autorEvent) return null;

  const unlinked = autorEvent.action.toLocaleLowerCase("es") === "desvincular";
  return {
    title: unlinked ? "Autor desvinculado" : "Autor vinculado",
    description: autorEvent.name
      ? `${autorEvent.name}${autorEvent.type ? ` (${autorEvent.type})` : ""}`
      : "Autor actualizado",
  };
}

export function presentTrabajoRevistaHistoryItems(items: HistorialTrabajoRevistaItem[]) {
  return items.filter(isVisibleTrabajoRevistaHistoryItem);
}
