import { http } from "@/lib/http";
import type { Moneda } from "@/utils/money";

export type Equipamiento = {
  id: number;
  denominacion: string;
  created_by: number | null;
  created_by_nombre?: string | null;
  created_at: string | null | undefined;
  updated_by?: number | null;
  updated_by_nombre?: string | null;
  updated_at?: string | null | undefined;
  deleted_by: number | null;
  deleted_by_nombre?: string | null;
  deleted_at: string | null | undefined;
  descripcion_breve: string;
  fecha_incorporacion: string;
  monto_invertido: number;
  moneda: Moneda;
  grupo_utn_id: number;
  grupo?: string | null;
};

export type HistorialEquipamientoItem = {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
};

export type EquipamientoPayload = {
  denominacion: string;
  descripcion_breve: string;
  fecha_incorporacion: string;
  monto_invertido: number;
  moneda?: Moneda;
  grupo_utn_id: number;
};

type EquipamientoBackend = Partial<Equipamiento> & { id: number };
type ApiListResponse<T> = T[] | { data?: T[] };

const normalizeEquipamiento = (item: EquipamientoBackend): Equipamiento => ({
  id: item.id,
  denominacion: item.denominacion ?? "",
  created_by: item.created_by ?? null,
  created_by_nombre: item.created_by_nombre ?? null,
  created_at: item.created_at ?? null,
  updated_by: item.updated_by ?? null,
  updated_by_nombre: item.updated_by_nombre ?? null,
  updated_at: item.updated_at ?? null,
  deleted_by: item.deleted_by ?? null,
  deleted_by_nombre: item.deleted_by_nombre ?? null,
  deleted_at: item.deleted_at ?? null,
  descripcion_breve: item.descripcion_breve ?? "",
  fecha_incorporacion: item.fecha_incorporacion ?? "",
  monto_invertido:
    typeof item.monto_invertido === "number"
      ? item.monto_invertido
      : Number(item.monto_invertido ?? 0),
  grupo_utn_id: item.grupo_utn_id ?? 0,
  moneda: item.moneda ?? "ARS",
  grupo: item.grupo ?? null,
});

export async function getEquipamiento(
  activos: "true" | "false" | "all" = "true"
): Promise<Equipamiento[]> {
  const response = await http<ApiListResponse<EquipamientoBackend>>(`/equipamiento/?activos=${activos}`);
  const items = Array.isArray(response)
    ? response
    : Array.isArray(response?.data)
      ? response.data
      : [];

  return items.map(normalizeEquipamiento);
}

export async function getEquipamientoById(id: number): Promise<Equipamiento> {
  const response = await http<EquipamientoBackend>(`/equipamiento/${id}`);
  return normalizeEquipamiento(response);
}

export async function getHistorialEquipamientoById(
  id: number
): Promise<HistorialEquipamientoItem[]> {
  const response = await http<ApiListResponse<HistorialEquipamientoItem>>(`/equipamiento/${id}/historial`, {
    method: "GET",
  });

  if (Array.isArray(response)) {
    return response;
  }

  if (Array.isArray(response?.data)) {
    return response.data;
  }

  return [];
}

export async function createEquipamiento(
  payload: EquipamientoPayload
): Promise<Equipamiento> {
  const response = await http<EquipamientoBackend>("/equipamiento/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeEquipamiento(response);
}

export async function updateEquipamiento(
  id: number,
  payload: Partial<EquipamientoPayload>
): Promise<Equipamiento> {
  const body: Record<string, unknown> = {};

  if ("denominacion" in payload) body.denominacion = payload.denominacion;
  if ("descripcion_breve" in payload) {
    body.descripcion_breve = payload.descripcion_breve;
  }
  if ("fecha_incorporacion" in payload) {
    body.fecha_incorporacion = payload.fecha_incorporacion;
  }
  if ("monto_invertido" in payload) body.monto_invertido = payload.monto_invertido;
  if ("moneda" in payload) body.moneda = payload.moneda;
  if ("grupo_utn_id" in payload) body.grupo_utn_id = payload.grupo_utn_id;

  const response = await http<EquipamientoBackend>(`/equipamiento/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

  return normalizeEquipamiento(response);
}

export async function deleteEquipamiento(
  id: number
): Promise<{ message: string }> {
  return http<{ message: string }>(`/equipamiento/${id}`, {
    method: "DELETE",
  });
}
