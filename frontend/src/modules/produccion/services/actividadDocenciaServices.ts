import { http } from "@/lib/http";

export interface ActividadDocencia {
  created_by: number | null;
  created_at: string | null | undefined;
  updated_by?: number | null;
  updated_at?: string | null | undefined;
  deleted_by: number | null;
  deleted_at: string | null | undefined;
  updated_by_nombre?: string | null;
  rol_actividad_id: number | null;
  grado_academico_id: number | null;
  id: number;
  curso: string;
  institucion: string;
  fecha_inicio: string;
  fecha_fin: string;
  grado_academico: string;
  grado_academico_actual?: { id: number; nombre: string } | null;
  historial_grados?: Array<{
    id: number | string;
    grado_academico?: string;
    fecha_inicio?: string | null;
    fecha_fin?: string | null;
    activo?: boolean;
  }>;
  rol_actividad: string;
  investigador_id: number;
  investigador?: string | { id: number; nombre_apellido: string };
}

type ActividadDocenciaApiResponse = Omit<
  ActividadDocencia,
  "grado_academico" | "rol_actividad"
> & {
  grado_academico?: string | { id: number; nombre: string } | null;
  rol_actividad?: string | { id: number; nombre: string } | null;
};

function getNombreCatalogo(
  value?: string | { id: number; nombre: string } | null
) {
  return typeof value === "string" ? value : value?.nombre ?? "";
}

function mapActividadDocencia(
  item: ActividadDocenciaApiResponse
): ActividadDocencia {
  return {
    ...item,
    grado_academico: getNombreCatalogo(item.grado_academico),
    rol_actividad: getNombreCatalogo(item.rol_actividad),
  };
}

export interface HistorialActividadDocenciaItem {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
}

export interface ActividadDocenciaPayload {
  curso: string;
  institucion: string;
  fecha_inicio: string;
  fecha_fin: string;
  grado_academico_id: number;
  rol_actividad_id: number;
  investigador_id: number;
}

export type DocenciaPageParams = {
  page: number; activos: "true" | "false" | "all"; q: string;
  sort: string; direction: "asc" | "desc"; ids?: Array<number | string>;
  filters: { curso?: string; institucion?: string; investigador?: string; grado?: string; rol?: string };
};

export async function getActividadesDocenciaPage(params: DocenciaPageParams) {
  const query = new URLSearchParams({ view: "table", page: String(params.page), per_page: "9",
    activos: params.activos, q: params.q, sort: params.sort, direction: params.direction });
  if (params.ids !== undefined) query.set("ids", params.ids.join(","));
  for (const [key, value] of Object.entries(params.filters)) {
    if (value) query.set(`filter_${key}`, value);
  }
  const result = await http<{ data: ActividadDocenciaApiResponse[]; meta: {
    total: number; total_pages: number; options: Record<string, Array<{ value: string; label: string }>>;
  } }>(`/actividades-docencia?${query}`);
  return { ...result, data: result.data.map(mapActividadDocencia) };
}

export const getActividadesDocencia = async (
  investigadorId?: number,
  activo: "true" | "false" | "all" = "true"
): Promise<ActividadDocencia[]> => {
  const params = new URLSearchParams();

  if (investigadorId) {
    params.append("investigador_id", String(investigadorId));
  }

  params.append("activos", activo);

  const query = params.toString();

  const data = await http<ActividadDocenciaApiResponse[]>(
    `/actividades-docencia${query ? `?${query}` : ""}`,
    {
      method: "GET",
    }
  );

  return data.map(mapActividadDocencia);
};

export const getActividadDocenciaById = async (
  id: number
): Promise<ActividadDocencia> => {
  const data = await http<ActividadDocenciaApiResponse>(`/actividades-docencia/${id}`, {
    method: "GET",
  });
  return mapActividadDocencia(data);
};

export const crearActividadDocencia = async (
  payload: ActividadDocenciaPayload
): Promise<ActividadDocencia> => {
  const data = await http<ActividadDocenciaApiResponse>(`/actividades-docencia/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapActividadDocencia(data);
};

export const actualizarActividadDocencia = async (
  id: number,
  payload: Partial<ActividadDocenciaPayload>
): Promise<ActividadDocencia> => {
  const data = await http<ActividadDocenciaApiResponse>(`/actividades-docencia/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  return mapActividadDocencia(data);
};

export const eliminarActividadDocencia = async (
  id: number
): Promise<{ message: string }> => {
  return http<{ message: string }>(`/actividades-docencia/${id}`, {
    method: "DELETE",
  });
};

export const getHistorialActividadDocenciaById = async (
  id: number
): Promise<HistorialActividadDocenciaItem[]> => {
  return http<HistorialActividadDocenciaItem[]>(
    `/actividades-docencia/${id}/historial`,
    {
      method: "GET",
    }
  );
};
