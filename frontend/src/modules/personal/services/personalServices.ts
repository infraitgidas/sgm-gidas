import { http } from "@/lib/http";

export type PersonalType =
  | "PERSONAL"
  | "PTAA"
  | "PROFESIONAL"
  | "BECARIO"
  | "INVESTIGADOR";

export interface PersonalItem {
  id: number;
  nombre_apellido: string;
  horas_semanales: number;
  tipo?: "PTAA" | "PROFESIONAL" | "BECARIO" | "INVESTIGADOR";
  activo: boolean;
  rol: "personal" | "becario" | "investigador";
  clasificacion?: string | null;
  grupo?: string | null;
  fecha_alta_grupo?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  deleted_at?: string | null;
}

export type PersonalSort = "nombre" | "clase" | "clasificacion" | "grupo" | "horas" | "estado" | "fecha_alta";

export interface PersonalListParams {
  page: number;
  perPage?: number;
  search?: string;
  tipo?: PersonalType;
  activos?: "true" | "false" | "all";
  sort?: PersonalSort;
  direction?: "asc" | "desc";
  ids?: Array<number | string>;
}

export interface PersonalPage {
  data: PersonalItem[];
  meta: { page: number; per_page: number; total: number; total_pages: number };
  error: null;
}
export interface PersonalPayload {
  nombre_apellido: string;
  dni: string;
  cuil: string;
  horas_semanales: number;
  fecha_alta_grupo: string;
  grupo_utn_id: number;
  tipo_personal_id: number;
  activo: boolean;
}


export function getPersonal(
  tipo?: PersonalType,
  activos: "true" | "false" | "all" = "true"
) {
  const params = new URLSearchParams();

  if (tipo) params.append("tipo", tipo);
  if (activos) params.append("activos", activos);

  const query = params.toString();

  return http<PersonalItem[]>(`/personal-all${query ? `?${query}` : ""}`);
}

export function getPersonalPage(params: PersonalListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    per_page: String(params.perPage ?? 9),
    activos: params.activos ?? "true",
    sort: params.sort ?? "fecha_alta",
    direction: params.direction ?? "desc",
  });
  if (params.search?.trim()) query.set("search", params.search.trim());
  if (params.tipo) query.set("tipo", params.tipo);
  if (params.ids) query.set("ids", params.ids.join(","));
  return http<PersonalPage>(`/personal/all?${query.toString()}`);
}

// 👉 POST / PUT PTAA + Profesional
export function upsertPersonal(payload: PersonalPayload) {
  return http<PersonalItem>("/personal", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function actualizarPersonal(id: number, payload: Partial<PersonalPayload>, rol: string) {
  return http<PersonalItem>(`/personal/${rol}/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function eliminarPersonal(id: number, rol: string) {
  return http<{ message: string }>(`/personal/${rol}/${id}`, {
    method: "DELETE",
  });
}

