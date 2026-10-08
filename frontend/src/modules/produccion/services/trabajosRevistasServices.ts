import type { AutorReferencia, IntegranteAutor } from "@/modules/produccion/services/trabajoAutoresServices";
import { http } from "@/lib/http";

export interface TrabajoRevista {
  id: number;
  created_by: number | null;
  created_by_nombre?: string | null;
  created_at: string | null | undefined;
  updated_by?: number | null;
  updated_by_nombre?: string | null;
  updated_at?: string | null | undefined;
  deleted_by: number | null;
  deleted_by_nombre?: string | null;
  deleted_at: string | null | undefined;
  activo?: boolean;
  enlace?: string | null;
  titulo_trabajo: string;
  nombre_revista: string;
  editorial: string;
  issn: string;
  pais: string;
  fecha_publicacion: string;
  grupo: string | null;
  tipo_revista?: {
    id: number;
    nombre: string;
  } | null;
  autores: IntegranteAutor[];
}

export interface HistorialTrabajoRevistaItem {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
}

export interface TrabajoRevistaPayload {
  autores: AutorReferencia[];
  enlace?: string | null;
  titulo_trabajo: string;
  nombre_revista: string;
  editorial: string;
  issn: string;
  pais: string;
  fecha_publicacion: string;
  tipo_revista_id?: number | null;
  grupo_utn_id?: number | null;
}

type GetTrabajosRevistasOptions = {
  activos?: "true" | "false" | "all";
  orden?: "asc" | "desc";
};

type TrabajoRevistaBackend = Partial<TrabajoRevista> & { id: number };
type ApiListResponse<T> = T[] | { data?: T[] };

const normalizeTrabajoRevista = (item: TrabajoRevistaBackend): TrabajoRevista => ({
  id: item.id,
  created_by: item.created_by ?? null,
  created_by_nombre: item.created_by_nombre ?? null,
  created_at: item.created_at ?? null,
  updated_by: item.updated_by ?? null,
  updated_by_nombre: item.updated_by_nombre ?? null,
  updated_at: item.updated_at ?? null,
  deleted_by: item.deleted_by ?? null,
  deleted_by_nombre: item.deleted_by_nombre ?? null,
  deleted_at: item.deleted_at ?? null,
  activo: item.activo ?? true,
  enlace: item.enlace ?? null,
  titulo_trabajo: item.titulo_trabajo ?? "",
  nombre_revista: item.nombre_revista ?? "",
  editorial: item.editorial ?? "",
  issn: item.issn ?? "",
  pais: item.pais ?? "",
  fecha_publicacion: item.fecha_publicacion ?? "",
  grupo: item.grupo ?? null,
  tipo_revista: item.tipo_revista ?? null,
  autores: Array.isArray(item.autores) ? item.autores : [],
});

export const getTrabajosRevistas = async (
  options: GetTrabajosRevistasOptions = {}
): Promise<TrabajoRevista[]> => {
  const { activos, orden = "asc" } = options;

  const params = new URLSearchParams();

  if (activos) {
    params.append("activos", activos);
  }

  if (orden) {
    params.append("orden", orden);
  }

  const query = params.toString();
  const endpoint = query
    ? `/trabajos-revistas?${query}`
    : "/trabajos-revistas";

  const response = await http<ApiListResponse<TrabajoRevistaBackend>>(endpoint, {
    method: "GET",
  });

  const items = Array.isArray(response)
    ? response
    : Array.isArray(response?.data)
      ? response.data
      : [];

  return items.map(normalizeTrabajoRevista);
};

export const getTrabajoRevistaById = async (id: number): Promise<TrabajoRevista> => {
  const response = await http<TrabajoRevistaBackend>(`/trabajos-revistas/${id}`, {
    method: "GET",
  });

  return normalizeTrabajoRevista(response);
};

export const getHistorialTrabajoRevistaById = async (
  id: number
): Promise<HistorialTrabajoRevistaItem[]> => {
  const response = await http<ApiListResponse<HistorialTrabajoRevistaItem>>(`/trabajos-revistas/${id}/historial`, {
    method: "GET",
  });

  if (Array.isArray(response)) {
    return response;
  }

  if (Array.isArray(response?.data)) {
    return response.data;
  }

  return [];
};

export const createTrabajoRevista = async (data: TrabajoRevistaPayload): Promise<TrabajoRevista> => {
  const response = await http<TrabajoRevistaBackend>("/trabajos-revistas/", {
    method: "POST",
    body: JSON.stringify(data),
  });

  return normalizeTrabajoRevista(response);
};

export const updateTrabajoRevista = async (
  id: number,
  data: Partial<TrabajoRevistaPayload>
): Promise<TrabajoRevista> => {
  const body: Record<string, unknown> = {};
  if ("autores" in data) body.autores = data.autores;

  if ("enlace" in data) body.enlace = data.enlace;
  if ("titulo_trabajo" in data) body.titulo_trabajo = data.titulo_trabajo;
  if ("nombre_revista" in data) body.nombre_revista = data.nombre_revista;
  if ("editorial" in data) body.editorial = data.editorial;
  if ("issn" in data) body.issn = data.issn;
  if ("pais" in data) body.pais = data.pais;
  if ("fecha_publicacion" in data) body.fecha_publicacion = data.fecha_publicacion;
  if ("tipo_revista_id" in data) body.tipo_revista_id = data.tipo_revista_id;
  if ("grupo_utn_id" in data) body.grupo_utn_id = data.grupo_utn_id;

  const response = await http<TrabajoRevistaBackend>(`/trabajos-revistas/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

  return normalizeTrabajoRevista(response);
};

export const deleteTrabajoRevista = async (id: number) =>
  http<{ message: string }>(`/trabajos-revistas/${id}`, {
    method: "DELETE",
  });
