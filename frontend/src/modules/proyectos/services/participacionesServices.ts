import { http } from "@/lib/http";

export type ParticipanteRol = "investigador" | "becario";

export interface ParticipanteRef {
  rol: ParticipanteRol;
  id: number;
}

export interface Participante extends ParticipanteRef {
  nombre_apellido: string;
  tipo: "Investigador" | "Becario";
}

export interface Participacion {
  id: number;
  nombre_evento: string;
  forma_participacion: string;
  fecha: string;
  participante: Participante;
  investigador_id?: number | null;
  becario_id?: number | null;
  created_at?: string | null;
  created_by?: number | null;
  created_by_nombre?: string | null;
  updated_at?: string | null;
  updated_by?: number | null;
  updated_by_nombre?: string | null;
  deleted_at?: string | null;
  deleted_by?: number | null;
  deleted_by_nombre?: string | null;
}

export interface HistorialParticipacionItem {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
}

export interface ParticipacionPayload {
  nombre_evento: string;
  forma_participacion: string;
  fecha: string;
  participante: ParticipanteRef;
}

export type GetParticipacionesOptions = {
  participante?: ParticipanteRef;
  orden?: "asc" | "desc";
  activos?: "true" | "false" | "all";
};

type ParticipacionApiResponse = Omit<Participacion, "participante"> & {
  participante?: Partial<Participante> | null;
  investigador?: string | { nombre_apellido?: string | null } | null;
};

type ApiListResponse<T> = T[] | { data?: T[] };

const normalizeParticipacion = (item: ParticipacionApiResponse): Participacion => {
  const rol: ParticipanteRol = item.participante?.rol === "becario" ? "becario" : "investigador";
  const legacyName =
    typeof item.investigador === "string"
      ? item.investigador
      : item.investigador?.nombre_apellido ?? "";
  const participanteId = Number(
    item.participante?.id ?? (rol === "becario" ? item.becario_id : item.investigador_id) ?? 0
  );

  return {
    ...item,
    nombre_evento: item.nombre_evento ?? "",
    forma_participacion: item.forma_participacion ?? "",
    fecha: item.fecha ?? "",
    participante: {
      rol,
      id: participanteId,
      nombre_apellido: item.participante?.nombre_apellido ?? legacyName,
      tipo: rol === "becario" ? "Becario" : "Investigador",
    },
  };
};

export const getParticipaciones = async (
  options: GetParticipacionesOptions = {}
): Promise<Participacion[]> => {
  const { participante, orden = "desc", activos } = options;
  const params = new URLSearchParams();
  if (participante) {
    params.set("participante_rol", participante.rol);
    params.set("participante_id", String(participante.id));
  }
  if (orden) params.set("orden", orden);
  if (activos) params.set("activos", activos);
  const query = params.toString();
  const response = await http<ApiListResponse<ParticipacionApiResponse>>(
    query ? `/participaciones-relevantes?${query}` : "/participaciones-relevantes",
    { method: "GET" }
  );
  const items = Array.isArray(response)
    ? response
    : Array.isArray(response?.data)
      ? response.data
      : [];
  return items.map(normalizeParticipacion);
};

export const getParticipacionById = async (id: number): Promise<Participacion> =>
  normalizeParticipacion(
    await http<ParticipacionApiResponse>(`/participaciones-relevantes/${id}`, {
      method: "GET",
    })
  );

export const getHistorialParticipacionById = async (
  id: number
): Promise<HistorialParticipacionItem[]> => {
  const response = await http<ApiListResponse<HistorialParticipacionItem>>(
    `/participaciones-relevantes/${id}/historial`,
    { method: "GET" }
  );
  return Array.isArray(response)
    ? response
    : Array.isArray(response?.data)
      ? response.data
      : [];
};

export const crearParticipacion = async (
  payload: ParticipacionPayload
): Promise<Participacion> =>
  normalizeParticipacion(
    await http<ParticipacionApiResponse>("/participaciones-relevantes/", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  );

export const actualizarParticipacion = async (
  id: number,
  payload: Partial<ParticipacionPayload>
): Promise<Participacion> =>
  normalizeParticipacion(
    await http<ParticipacionApiResponse>(`/participaciones-relevantes/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    })
  );

export const eliminarParticipacion = (id: number) =>
  http<{ message: string }>(`/participaciones-relevantes/${id}`, {
    method: "DELETE",
  });
