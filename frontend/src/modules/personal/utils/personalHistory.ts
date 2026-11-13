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
  const labels: Record<string, string> = {
    tipo_personal_id: "Tipo de Personal",
    tipo_formacion_id: "Nivel de Formación",
    tipo_dedicacion_id: "Tipo de Dedicación",
    categoria_utn_id: "Categoría UTN",
    programa_incentivos_id: "Programa de Incentivos",
    grupo_utn_id: "Grupo de investigación (UCT)",
    fecha_alta_grupo: "Fecha de alta en el grupo",
    nombre_apellido: "Nombre y apellido",
    clase_registro: "Clase de registro",
  };
  if (labels[value]) return labels[value];
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
  if (!match) return null;
  const date = new Date(`${value}T00:00:00`);
  return date.getFullYear() === Number(match[1]) && date.getMonth() + 1 === Number(match[2]) && date.getDate() === Number(match[3])
    ? `${match[3]}/${match[2]}/${match[1]}` : null;
}

function formatAmount(value: unknown) {
  if (typeof value === "string" && /^\d+(?:\.\d+)?$/.test(value.trim())) value = Number(value);
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return `ARS ${new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 }).format(value)}`;
}

function decodeScholarshipValue(value: unknown): unknown {
  // Admite texto JSON almacenado dentro de la columna JSON sin reescribirlo.
  for (let depth = 0; depth < 2 && typeof value === "string"; depth++) {
    try { value = JSON.parse(value); } catch { return null; }
  }
  return value;
}

function formatScholarshipDetail(value: unknown): string | null {
  const detail = decodeScholarshipValue(value);
  if (!isRecord(detail)) return null;
  const parts: string[] = [];
  if (typeof detail.nombre_beca === "string" && detail.nombre_beca.trim() && !/[{}\[\]]/.test(detail.nombre_beca)) {
    parts.push(detail.nombre_beca.trim());
  } else if (typeof detail.beca_id === "number" && Number.isInteger(detail.beca_id) && detail.beca_id > 0) {
    parts.push(`Beca #${detail.beca_id}`);
  }
  const start = formatCivilDate(detail.fecha_inicio);
  const end = formatCivilDate(detail.fecha_fin);
  const amount = formatAmount(detail.monto_percibido);
  if (start) parts.push(`Inicio: ${start}`);
  if (detail.fecha_fin === null) parts.push("Sin fecha de fin");
  else if (end) parts.push(`Fin: ${end}`);
  if (detail.monto_percibido === null) parts.push("Monto: sin registrar");
  else if (amount) parts.push(`Monto: ${amount}`);
  return parts.join(" · ") || null;
}

function formatScholarshipEvent(value: unknown): HistoryPresentation | null {
  value = decodeScholarshipValue(value);
  if (!isRecord(value) || typeof value.accion !== "string") return null;
  const actionLabels: Record<string, string> = {
    vincular: "Beca vinculada",
    actualizar: "Beca actualizada",
    desvincular: "Beca desvinculada",
  };
  const title = Object.prototype.hasOwnProperty.call(actionLabels, value.accion) ? actionLabels[value.accion] : null;
  if (!title) return null;
  const description = formatScholarshipDetail(value.detalle);
  return description ? { title, description } : null;
}

function formatScholarshipSnapshot(value: unknown): string | null {
  value = decodeScholarshipValue(value);
  if (!Array.isArray(value)) return formatScholarshipDetail(value);
  if (!value.length) return "Sin becas asignadas";
  const summaries = value.map(formatScholarshipDetail);
  return summaries.every(Boolean) ? summaries.join("; ") : null;
}

export function formatPersonalHistoryEntry(entry: HistorialCambioItem): HistoryPresentation {
  if (entry.campo === "becas") {
    const scholarship = formatScholarshipEvent(entry.valor_nuevo);
    if (scholarship) return scholarship;
    const before = formatScholarshipSnapshot(entry.valor_anterior);
    const after = formatScholarshipSnapshot(entry.valor_nuevo);
    return {
      title: "Becas actualizadas",
      description: before && after ? `${before} → ${after}`
        : after || before || "Se registró un cambio en las becas asignadas.",
    };
  }

  return {
    title: formatLabel(entry.campo || entry.tipo),
    description: `${formatValue(entry.valor_anterior_nombre ?? entry.valor_anterior)} → ${formatValue(entry.valor_nuevo_nombre ?? entry.valor_nuevo)}`,
  };
}
