import { http } from "@/lib/http";

export interface Distincion {
  id: number;
  fecha: string;
  descripcion: string;
  proyecto?: {
    id: number;
    codigo: string;
    nombre: string;
  } | null;
  created_by?: number | null;
  created_by_nombre?: string | null;
  created_at?: string | null;
  updated_by?: number | null;
  updated_by_nombre?: string | null;
  updated_at?: string | null;
  deleted_by?: number | null;
  deleted_by_nombre?: string | null;
  deleted_at?: string | null;
  activo?: boolean;
}

export interface HistorialDistincionItem {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
}

export interface DistincionPayload {
  fecha: string;
  descripcion: string;
  proyecto_investigacion_id?: number | null;
}

type GetDistincionesOptions = {
  proyectoId?: number;
  activos?: "true" | "false" | "all";
  orden?: "asc" | "desc";
};

type DistincionBackend = Partial<Distincion> & { id: number };
type ApiListResponse<T> = T[] | { data?: T[] };

const normalizeDistincion = (item: DistincionBackend): Distincion => ({
  id: item.id,
  fecha: item.fecha ?? "",
  descripcion: item.descripcion ?? "",
  proyecto: item.proyecto ?? null,
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
});

export const getDistinciones = async (
  options: GetDistincionesOptions = {}
): Promise<Distincion[]> => {
  const { proyectoId, activos, orden = "asc" } = options;

  const params = new URLSearchParams();
  if (proyectoId) params.append("proyecto_id", String(proyectoId));
  if (activos) params.append("activos", activos);
  if (orden) params.append("orden", orden);

  const query = params.toString();
  const endpoint = query ? `/distinciones/?${query}` : "/distinciones/";

  const response = await http<ApiListResponse<DistincionBackend>>(endpoint, { method: "GET" });
  const items = Array.isArray(response)
    ? response
    : Array.isArray(response?.data)
      ? response.data
      : [];

  return items.map(normalizeDistincion);
};

export const getDistincionById = async (id: number): Promise<Distincion> => {
  const response = await http<DistincionBackend>(`/distinciones/${id}`, { method: "GET" });
  return normalizeDistincion(response);
};

export const getHistorialDistincionById = async (
  id: number
): Promise<HistorialDistincionItem[]> => {
  const response = await http<ApiListResponse<HistorialDistincionItem>>(`/distinciones/${id}/historial`, {
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

export const crearDistincion = async (
  payload: DistincionPayload
): Promise<Distincion> => {
  const response = await http<DistincionBackend>("/distinciones/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeDistincion(response);
};

export const actualizarDistincion = async (
  id: number,
  payload: Partial<DistincionPayload>
): Promise<Distincion> => {
  const body: Record<string, unknown> = {};

  if ("fecha" in payload) body.fecha = payload.fecha;
  if ("descripcion" in payload) body.descripcion = payload.descripcion;
  if ("proyecto_investigacion_id" in payload) {
    body.proyecto_investigacion_id = payload.proyecto_investigacion_id;
  }

  const response = await http<DistincionBackend>(`/distinciones/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

  return normalizeDistincion(response);
};

export const eliminarDistincion = async (
  id: number
): Promise<{ message: string }> => {
  return http<{ message: string }>(`/distinciones/${id}`, { method: "DELETE" });
};
