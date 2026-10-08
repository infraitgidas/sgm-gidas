import { http } from "@/lib/http";

export type Visitante = {
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
  razon: string;
  fecha: string;
  procedencia: string;
  tipo_visita_id: number;
  grupo_utn_id: number;
  tipo_visita?: {
    id: number;
    nombre: string;
  };
  grupo?: string | null;
};

export type HistorialVisitanteItem = {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
};

export type VisitantePayload = {
  razon: string;
  fecha: string;
  procedencia: string;
  tipo_visita_id: number;
  grupo_utn_id: number;
};

export type GrupoUtnOption = {
  id: number;
  nombre: string;
};

type VisitanteApiResponse = Omit<Visitante, "tipo_visita"> & {
  tipo_visita?: Visitante["tipo_visita"];
};

type ApiListResponse<T> = T[] | { data?: T[] };

type GrupoUtnApiResponse = {
  id: number;
  nombre_sigla_grupo?: string;
  nombre?: string;
};

const normalizeVisitante = (item: VisitanteApiResponse): Visitante => ({
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
  razon: item.razon ?? "",
  fecha: item.fecha ?? "",
  procedencia: item.procedencia ?? "",
  tipo_visita_id: item.tipo_visita_id,
  grupo_utn_id: item.grupo_utn_id,
  tipo_visita: item.tipo_visita ?? undefined,
  grupo: item.grupo ?? null,
});

export async function getVisitantes(
  activos: "true" | "false" | "all" = "true"
): Promise<Visitante[]> {
  const response = await http<ApiListResponse<VisitanteApiResponse>>(
    `/visitas-academicas/?activos=${activos}`
  );
  const items = Array.isArray(response)
    ? response
    : Array.isArray(response?.data)
      ? response.data
      : [];

  return items.map(normalizeVisitante);
}

export async function getVisitanteById(id: number): Promise<Visitante> {
  const response = await http<VisitanteApiResponse>(`/visitas-academicas/${id}`);
  return normalizeVisitante(response);
}

export async function getHistorialVisitanteById(
  id: number
): Promise<HistorialVisitanteItem[]> {
  const response = await http<ApiListResponse<HistorialVisitanteItem>>(
    `/visitas-academicas/${id}/historial`, {
    method: "GET",
    }
  );

  if (Array.isArray(response)) {
    return response;
  }

  if (Array.isArray(response?.data)) {
    return response.data;
  }

  return [];
}

export async function crearVisitante(
  payload: VisitantePayload
): Promise<Visitante> {
  const response = await http<VisitanteApiResponse>("/visitas-academicas/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeVisitante(response);
}

export async function actualizarVisitante(
  id: number,
  payload: Partial<VisitantePayload>
): Promise<Visitante> {
  const body: Record<string, unknown> = {};

  if ("razon" in payload) body.razon = payload.razon;
  if ("fecha" in payload) body.fecha = payload.fecha;
  if ("procedencia" in payload) body.procedencia = payload.procedencia;
  if ("tipo_visita_id" in payload) body.tipo_visita_id = payload.tipo_visita_id;
  if ("grupo_utn_id" in payload) body.grupo_utn_id = payload.grupo_utn_id;

  const response = await http<VisitanteApiResponse>(`/visitas-academicas/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

  return normalizeVisitante(response);
}

export async function eliminarVisitante(id: number): Promise<{ message: string }> {
  return http<{ message: string }>(`/visitas-academicas/${id}`, {
    method: "DELETE",
  });
}

export async function getGruposUtn() {
  const data = await http<GrupoUtnApiResponse[] | GrupoUtnApiResponse>("/grupo-utn/");

  const grupos = Array.isArray(data) ? data : data ? [data] : [];
  return grupos.map((g) => ({
    id: g.id,
    nombre: g.nombre_sigla_grupo || g.nombre || "Grupo sin nombre",
  }));
}
