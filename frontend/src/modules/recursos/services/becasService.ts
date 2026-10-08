import { http } from "@/lib/http";

export interface Beca {
  id: number;
  grupo_utn_id?: number | null;
  nombre_beca: string;
  descripcion?: string | null;
  fecha_alta_grupo?: string | null;
  fuente_financiamiento_id?: number | null;
  fuente_financiamiento?: { id: number; nombre: string } | null;
  becarios?: { id: number; nombre_apellido: string; fecha_inicio: string; fecha_fin: string | null; monto_percibido: number | null }[];
  created_at?: string;
  creator_name?: string;
  created_by_nombre?: string;
  updated_at?: string;
  updated_by_nombre?: string;
  deleted_at?: string | null;
  deleter_name?: string;
  deleted_by_nombre?: string;
  activo?: boolean;
}

export type BecaPayload = { nombre_beca: string; descripcion?: string | null; fecha_alta_grupo?: string | null; fuente_financiamiento_id?: number | null };
export type BecaHistorial = { id: number; campo?: string; fecha_cambio?: string; usuario_nombre?: string; valor_anterior?: unknown; valor_nuevo?: unknown; tipo?: string };
export type BecaVencimiento = { vinculacion_id: number; becario_id: number; becario: string; beca_id: number; beca: string; fecha_fin: string; dias_restantes: number };
export type BecasPage = { data: Beca[]; meta: { page: number; per_page: number; total: number; total_pages: number } };
export interface BecaVinculacionPayload { id_becario: number; fecha_inicio: string; fecha_fin?: string; monto_percibido?: number }

export function getBecas() { return http<Beca[]>("/becas/", { method: "GET" }); }
export function getBecasPage(page: number, activos: "true" | "false" | "all" = "true", search = "") { return http<BecasPage>(`/becas/?page=${page}&per_page=9&activos=${activos}&q=${encodeURIComponent(search)}`, { method: "GET" }); }
export function getBecaById(id: number) { return http<Beca>(`/becas/${id}`, { method: "GET" }); }
export function createBeca(payload: BecaPayload) { return http<Beca>("/becas/", { method: "POST", body: JSON.stringify(payload) }); }
export function updateBeca(id: number, payload: Partial<BecaPayload>) { return http<Beca>(`/becas/${id}`, { method: "PUT", body: JSON.stringify(payload) }); }
export function deleteBeca(id: number) { return http<{ message: string }>(`/becas/${id}`, { method: "DELETE" }); }
export function getBecaHistorial(id: number) { return http<BecaHistorial[]>(`/becas/${id}/historial`, { method: "GET" }); }
export function getBecasProximasAVencer() { return http<BecaVencimiento[]>("/becas/proximas-a-vencer", { method: "GET" }); }
export function vincularBecarioABeca(beca_id: number, payload: BecaVinculacionPayload) { return http(`/becas/${beca_id}/vincular-becario`, { method: "POST", body: JSON.stringify(payload) }); }
export function desvincularBecarioDeBeca(beca_id: number, becario_id: number) { return http(`/becas/${beca_id}/becarios/${becario_id}`, { method: "DELETE" }); }
