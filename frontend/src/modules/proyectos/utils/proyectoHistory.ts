import type { HistorialProyectoItem } from "@/modules/proyectos/services/proyectosServices";

type HistoryPresentation = { title: string; description: string };

type ProyectoPersonal = {
  investigadores?: Array<{ id: number; nombre_apellido: string }>;
  becarios?: Array<{ id: number; nombre_apellido: string }>;
};

const FIELD_LABELS: Record<string, string> = {
  codigo_proyecto: "Código del proyecto",
  nombre_proyecto: "Nombre del proyecto",
  descripcion_proyecto: "Descripción",
  logros_obtenidos: "Logros obtenidos",
  dificultades_proyecto: "Dificultades",
  monto_destinado: "Monto destinado",
  fecha_inicio: "Fecha de inicio",
  fecha_fin: "Fecha de finalización",
  tipo_proyecto_id: "Tipo de proyecto",
  fuente_financiamiento_id: "Fuente de financiamiento",
  coordinador_id: "Coordinador",
  investigadores: "Investigadores",
  investigadores_ids: "Investigadores",
  becarios: "Becarios",
  becarios_ids: "Becarios",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function label(value?: string) {
  if (!value) return "Cambio";
  return FIELD_LABELS[value] ?? value.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase());
}

function valueLabel(value: unknown, field?: string) {
  if (value === null || value === undefined || value === "") return "Sin dato";
  if (field === "fecha_inicio" || field === "fecha_fin") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
    return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value);
  }
  if (typeof value === "boolean") return value ? "Sí" : "No";
  return String(value);
}

function relationEvent(
  entry: HistorialProyectoItem,
  personal?: ProyectoPersonal
): HistoryPresentation | null {
  if (!isRecord(entry.valor_nuevo) || typeof entry.valor_nuevo.accion !== "string") return null;
  const detail = isRecord(entry.valor_nuevo.detalle) ? entry.valor_nuevo.detalle : {};
  const actionLabels: Record<string, string> = { vincular: "vinculado", desvincular: "desvinculado", actualizar: "actualizado" };
  const action = actionLabels[entry.valor_nuevo.accion] ?? entry.valor_nuevo.accion;
  const isBecario = entry.campo === "becarios" || entry.campo === "becarios_ids";
  const singular = isBecario ? "Becario" : "Investigador";
  const collection = isBecario ? personal?.becarios : personal?.investigadores;
  const id = typeof detail.id === "number" ? detail.id : null;
  const storedName = typeof detail.nombre_apellido === "string" ? detail.nombre_apellido.trim() : "";
  const currentName = id === null ? "" : collection?.find((item) => item.id === id)?.nombre_apellido ?? "";
  return { title: `${singular} ${action}`, description: storedName || currentName || singular };
}

function coordinatorEvent(
  entry: HistorialProyectoItem,
  personal?: ProyectoPersonal
): HistoryPresentation | null {
  if (entry.campo !== "coordinador_id") return null;

  const value = entry.valor_nuevo;
  if (value === null || value === undefined || value === "") return null;

  const detail = isRecord(value) ? value : null;
  const idValue = detail?.id ?? value;
  const id = typeof idValue === "number"
    ? idValue
    : typeof idValue === "string" && idValue.trim()
      ? Number(idValue)
      : NaN;
  const storedName = typeof detail?.nombre_apellido === "string"
    ? detail.nombre_apellido.trim()
    : "";
  const currentName = Number.isFinite(id)
    ? personal?.investigadores?.find((item) => item.id === id)?.nombre_apellido ?? ""
    : "";

  return {
    title: "Coordinador asignado",
    description: storedName || currentName || "Coordinador actualizado",
  };
}

export function formatProyectoRelationHistoryEntry(
  entry: HistorialProyectoItem,
  personal?: ProyectoPersonal
): HistoryPresentation | null {
  if (entry.campo === "prorroga" && isRecord(entry.valor_nuevo)) {
    const fecha = entry.valor_nuevo.fecha_fin;
    const motivo = entry.valor_nuevo.motivo;
    return {
      title: "Prórroga de 12 meses",
      description: `Nuevo fin: ${typeof fecha === "string" ? valueLabel(fecha, "fecha_fin") : "-"}. Justificación: ${typeof motivo === "string" ? motivo : "-"}`,
    };
  }
  const coordinator = coordinatorEvent(entry, personal);
  if (coordinator) return coordinator;

  if (!["investigadores", "investigadores_ids", "becarios", "becarios_ids"].includes(entry.campo ?? "")) {
    return null;
  }

  return relationEvent(entry, personal);
}

export function formatProyectoHistoryEntry(
  entry: HistorialProyectoItem,
  personal?: ProyectoPersonal
): HistoryPresentation {
  const relation = formatProyectoRelationHistoryEntry(entry, personal);
  if (relation) return relation;
  return { title: label(entry.campo || entry.tipo), description: `${valueLabel(entry.valor_anterior, entry.campo)} → ${valueLabel(entry.valor_nuevo, entry.campo)}` };
}
