import type { InformePayload, InformeTipo } from "@/modules/informes/services/informesService";
import { getLocalTodayIso, isInstitutionalDate } from "@/utils/dateTime";

export function validateInforme(payload: InformePayload, tipo: InformeTipo): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!payload.memoria_id) errors.memoria_id = "Seleccione una Memoria.";
  for (const field of ["titulo", "resumen", "actividades", "resultados", "observaciones"] as const) {
    const max = field === "titulo" ? 200 : 20000;
    if (!payload[field].trim() || payload[field].trim().length > max) errors[field] = `Ingrese entre 1 y ${max} caracteres.`;
  }
  if (!isInstitutionalDate(payload.fecha_realizacion) || payload.fecha_realizacion > getLocalTodayIso()) errors.fecha_realizacion = "Seleccione una fecha entre el 01/01/2010 y hoy.";
  if (tipo !== "uct" && !payload.vinculos_ids.length) errors.vinculos_ids = "Seleccione al menos un registro.";
  return errors;
}

export function diffInforme(original: InformePayload, next: InformePayload) {
  const changed = Object.fromEntries(Object.entries(next).filter(([key, value]) => {
    if (key === "memoria_id") return false;
    const before = original[key as keyof InformePayload];
    return Array.isArray(value) && Array.isArray(before)
      ? value.length !== before.length || value.some((id) => !before.includes(id))
      : value !== before;
  }));
  return changed;
}
