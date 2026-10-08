import type { HistorialTransferenciaItem } from "@/modules/transferencia/services/transferenciasServices";

const labels: Record<string, string> = { denominacion: "Denominación", demandante: "Demandante", descripcion_actividad: "Descripción de la actividad", monto: "Monto", fecha_inicio: "Fecha de inicio", fecha_fin: "Fecha de fin", tipo_contrato_id: "Tipo de contrato", grupo_utn_id: "Grupo UTN" };
const object = (value: unknown): Record<string, unknown> | null => value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
const empty = (value: unknown) => value === null || value === undefined || value === "";
const readable = (value: unknown) => {
  if (empty(value)) return "Sin dato";
  const record = object(value);
  if (record) return String(record.nombre ?? record.nombre_sigla_grupo ?? record.label ?? "Dato actualizado");
  return String(value);
};

export function transferenciaHistoryEvent(item: HistorialTransferenciaItem) {
  if (item.campo !== "adoptantes") return null;
  const source = object(item.valor_nuevo);
  if (!source) return null;
  const detail = object(source.detalle) ?? source;
  return { title: source.accion === "desvincular" ? "Adoptante desvinculado" : "Adoptante vinculado", description: typeof detail.nombre === "string" && detail.nombre.trim() ? detail.nombre.trim() : "Adoptante actualizado" };
}

export function presentTransferenciaHistory(items: HistorialTransferenciaItem[]) {
  return items.filter(item => {
    const field = item.campo?.toLocaleLowerCase("es") ?? "";
    if (!field || field === "accion" || field === "acciones") return false;
    if (transferenciaHistoryEvent(item)) return true;
    if (Object.is(item.valor_anterior, item.valor_nuevo) || JSON.stringify(item.valor_anterior) === JSON.stringify(item.valor_nuevo)) return false;
    return !(empty(item.valor_anterior) && !empty(item.valor_nuevo));
  });
}

export function formatTransferenciaHistory(item: HistorialTransferenciaItem) {
  const event = transferenciaHistoryEvent(item);
  if (event) return event;
  const field = item.campo ?? "";
  const title = labels[field] ?? field.replace(/_id$/, "").replace(/_/g, " ").replace(/^./, letter => letter.toLocaleUpperCase("es"));
  const formatValue = (value: unknown) => {
    if (empty(value)) return "Sin dato";
    if (field === "monto") return new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(Number(value));
    if (field.startsWith("fecha_")) { const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value)); if (match) return `${match[3]}/${match[2]}/${match[1]}`; }
    if (field.endsWith("_id") && typeof value === "number") return "Dato actualizado";
    return readable(value);
  };
  return { title, description: `${formatValue(item.valor_anterior)} → ${formatValue(item.valor_nuevo)}` };
}
