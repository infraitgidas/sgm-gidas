import { http } from "@/lib/http";
import type { HistorialCambioCardItem } from "@/components/HistorialCambiosCard";

export type InformeTipo = "investigadores" | "pid" | "uct";
export const informeTipos: InformeTipo[] = ["investigadores", "pid", "uct"];
export const informeTipoLabel: Record<InformeTipo, string> = {
  investigadores: "Investigadores", pid: "PID", uct: "UCT",
};

export type InformeVinculo = { id: number; snapshot: Record<string, string | number | null> };
export type Informe = {
  id: number;
  tipo: InformeTipo;
  memoria_id: number;
  grupo_utn_id: number;
  periodo_inicio: string;
  periodo_fin: string;
  titulo: string;
  fecha_realizacion: string;
  autor: string | null;
  resumen: string;
  actividades: string;
  resultados: string;
  observaciones: string;
  uct_snapshot: { _version: number; nombre_sigla_grupo: string; nombre_unidad_academica: string; objetivo_desarrollo: string; mail: string };
  investigadores?: InformeVinculo[];
  proyectos?: InformeVinculo[];
  created_at: string;
  created_by_nombre: string | null;
  updated_at: string | null;
  updated_by_nombre: string | null;
  deleted_at: string | null;
  activo: boolean;
};
export type InformePayload = Pick<Informe, "memoria_id" | "titulo" | "fecha_realizacion" | "resumen" | "actividades" | "resultados" | "observaciones"> & { vinculos_ids: number[] };
export type InformePatch = Partial<Omit<InformePayload, "memoria_id">>;
export type InformeSummary = Pick<Informe, "id" | "tipo" | "memoria_id" | "grupo_utn_id" | "periodo_inicio" | "periodo_fin" | "titulo" | "fecha_realizacion" | "autor" | "activo" | "deleted_at">;
export type InformePage = { data: InformeSummary[]; meta: { page: number; per_page: number; total: number; total_pages: number }; error: null };

export function getInformes(tipo: InformeTipo, page: number, memoriaId?: number) {
  const query = new URLSearchParams({ page: String(page), per_page: "9" });
  if (memoriaId) query.set("memoria_id", String(memoriaId));
  return http<InformePage>(`/informes/${tipo}?${query}`);
}
export function getInforme(tipo: InformeTipo, id: number) {
  return http<Informe>(`/informes/${tipo}/${id}`);
}
export function getInformeHistorial(tipo: InformeTipo, id: number) {
  return http<HistorialCambioCardItem[]>(`/informes/${tipo}/${id}/historial`);
}
export type InformeCandidate = { id: number; name: string; activo: boolean };
export type InformeCandidatePage = { data: InformeCandidate[]; meta: InformePage["meta"]; error: null };
export function getInformeCandidates(tipo: InformeTipo, memoriaId: number, search: string, page: number) {
  const query = new URLSearchParams({ memoria_id: String(memoriaId), search, page: String(page), per_page: "9" });
  return http<InformeCandidatePage>(`/informes/${tipo}/candidatos?${query}`);
}
export function createInforme(tipo: InformeTipo, payload: InformePayload) {
  return http<Informe>(`/informes/${tipo}`, { method: "POST", body: JSON.stringify(payload) });
}
export function updateInforme(tipo: InformeTipo, id: number, payload: InformePatch) {
  return http<Informe>(`/informes/${tipo}/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}
export function deleteInforme(tipo: InformeTipo, id: number) {
  return http<{ message: string }>(`/informes/${tipo}/${id}`, { method: "DELETE" });
}
