import type {
  HistorialVisitanteItem,
  Visitante,
} from "@/modules/grupo/services/visitantesServices";

type VisitHistoryContext = {
  tiposVisita: ReadonlyMap<number, string>;
  visita?: Visitante;
};

const FIELD_LABELS: Record<string, string> = {
  razon: "Razón de la visita",
  fecha: "Fecha",
  procedencia: "Procedencia u origen",
  tipo_visita_id: "Tipo de visita",
  grupo_utn_id: "Grupo UTN",
};

const isEmpty = (value: unknown) =>
  value === null || value === undefined || value === "";

const areEquivalent = (previous: unknown, next: unknown) => {
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
};

const formatDate = (value: unknown) => {
  const text = String(value ?? "");
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : text;
};

function formatValue(
  item: HistorialVisitanteItem,
  value: unknown,
  context: VisitHistoryContext
) {
  if (isEmpty(value)) return "-";

  if (item.campo === "tipo_visita_id") {
    const id = Number(value);
    return (
      context.tiposVisita.get(id) ||
      (context.visita?.tipo_visita_id === id
        ? context.visita.tipo_visita?.nombre
        : undefined) ||
      "Tipo de visita no disponible"
    );
  }

  if (item.campo === "grupo_utn_id") {
    return Number(value) === context.visita?.grupo_utn_id
      ? context.visita.grupo || "Grupo no informado"
      : "Grupo no disponible";
  }

  if (item.campo === "fecha") return formatDate(value);
  if (typeof value === "object") return "Información actualizada";
  return String(value);
}

export function isVisibleVisitHistoryItem(item: HistorialVisitanteItem) {
  const field = item.campo?.trim().toLocaleLowerCase("es") ?? "";
  const type = item.tipo?.trim().toLocaleLowerCase("es") ?? "";
  if (!field || field === "accion" || field === "acciones" || type === "creacion") {
    return false;
  }
  if (areEquivalent(item.valor_anterior, item.valor_nuevo)) return false;
  return !(isEmpty(item.valor_anterior) && !isEmpty(item.valor_nuevo));
}

export function presentVisitHistoryItems(items: HistorialVisitanteItem[]) {
  return items.filter(isVisibleVisitHistoryItem);
}

export function formatVisitHistoryEntry(
  item: HistorialVisitanteItem,
  context: VisitHistoryContext
) {
  const title = item.campo
    ? FIELD_LABELS[item.campo] ||
      item.campo
        .replace(/_id$/, "")
        .replace(/_/g, " ")
        .replace(/^./, (letter) => letter.toLocaleUpperCase("es"))
    : "Cambio en la visita";
  const previous = formatValue(item, item.valor_anterior, context);
  const next = formatValue(item, item.valor_nuevo, context);

  return {
    title,
    description: `${previous} → ${next}`,
  };
}
