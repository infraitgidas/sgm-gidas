import type { HistorialCambioItem } from "@/modules/personal/services/personalCompletoServices";

type HistoryPresentation = {
  title: string;
  description: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatLabel(value?: string) {
  if (!value) return "Cambio";
  if (value === "dni" || value === "cuil") return value.toUpperCase();
  const normalized = value.endsWith("_id") ? value.slice(0, -3) : value;
  const label = normalized.replace(/_/g, " ");
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`;
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "Sin dato";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  return String(value);
}

function formatCivilDate(value: unknown) {
  if (typeof value !== "string") return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value;
}

function formatAmount(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return `ARS ${new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 }).format(value)}`;
}

function formatScholarshipEvent(value: unknown): HistoryPresentation | null {
  if (!isRecord(value) || typeof value.accion !== "string" || !isRecord(value.detalle)) return null;
  const actionLabels: Record<string, string> = {
    vincular: "Beca vinculada",
    actualizar: "Beca actualizada",
    desvincular: "Beca desvinculada",
  };
  const title = actionLabels[value.accion];
  if (!title) return null;

  const detail = value.detalle;
  const parts: string[] = [];
  if (typeof detail.beca_id === "number") parts.push(`Beca #${detail.beca_id}`);
  const start = formatCivilDate(detail.fecha_inicio);
  const end = formatCivilDate(detail.fecha_fin);
  const amount = formatAmount(detail.monto_percibido);
  if (start) parts.push(`Inicio: ${start}`);
  if (detail.fecha_fin === null) parts.push("Sin fecha de fin");
  else if (end) parts.push(`Fin: ${end}`);
  if (amount) parts.push(`Monto: ${amount}`);

  return { title, description: parts.join(" · ") || "Relación de beca modificada" };
}

export function formatPersonalHistoryEntry(entry: HistorialCambioItem): HistoryPresentation {
  if (entry.campo === "becas") {
    const scholarship = formatScholarshipEvent(entry.valor_nuevo);
    if (scholarship) return scholarship;
  }

  return {
    title: formatLabel(entry.campo || entry.tipo),
    description: `${formatValue(entry.valor_anterior)} → ${formatValue(entry.valor_nuevo)}`,
  };
}
