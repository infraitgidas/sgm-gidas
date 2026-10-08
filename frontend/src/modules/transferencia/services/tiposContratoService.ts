import { http } from "@/lib/http";

// ─── Tipos ───────────────────────────────────────────────────

export interface TipoContratoItem {
  id: number;
  nombre: string;
}

/** Los 6 tipos de contrato definidos en la especificación (fallback estático). */
export const TIPOS_CONTRATO_STATIC = [
  "Transferencia de Tecnología",
  "I+D+i",
  "Transferencia de conocimientos",
  "Asistencia Técnica o consultoría",
  "Servicios Técnicos / de apoyo / supervisión y/o Ensayos de Laboratorio",
  "Difusión a la comunidad académica y general",
] as const;

// ─── Helpers ─────────────────────────────────────────────────

/** El módulo usa siempre el backend para mantener coherentes catálogos y vínculos. */
export function isMockMode(): boolean {
  return false;
}

// ─── API ─────────────────────────────────────────────────────

/** Obtener los tipos de contrato del backend. */
export async function getTiposContrato(): Promise<TipoContratoItem[]> {
  if (isMockMode()) {
    return TIPOS_CONTRATO_STATIC.map((nombre, i) => ({
      id: i + 1,
      nombre,
    }));
  }
  return http<TipoContratoItem[]>("/tipo-contrato/");
}
