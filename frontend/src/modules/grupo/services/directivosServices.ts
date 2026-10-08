// src/services/directivoServices.ts
import { http } from "@/lib/http";

export type Directivo = {
  id: number;
  grupo_utn_id?: number | null;
  nombre_apellido: string;
};

export type DirectivoActual = {
  id_directivo: number;
  nombre_apellido: string;
  cargo: string;
  fecha_inicio: string;
  fecha_fin?: string | null;
};

export type DirectivoPeriodo = DirectivoActual & {
  id: number;
  fecha_fin: string | null;
};

export type CambioDirectivo = {
  id: number;
  entidad: "directivo" | "directivo_grupo";
  campo: "nombre_apellido" | "mandato";
  valor_anterior: string | null;
  valor_nuevo: string | {
    accion: "asignado" | "finalizado";
    detalle: { nombre_apellido: string; cargo: string; fecha_inicio: string; fecha_fin: string | null };
  };
  fecha_cambio: string;
  usuario_nombre: string | null;
};

export type CambiosDirectivosPage = {
  items: CambioDirectivo[];
  page: number;
  per_page: number;
  total: number;
};

export type UpdateDirectivoPayload = {
  nombre_apellido: string;
};

export type FinalizarDirectivoPayload = {
  id_grupo_utn: number;
  id_directivo: number;
  fecha_fin: string;
};

export function getDirectivos() {
  return http<Directivo[]>("/directivos", {
    method: "GET",
  });
}

export function createDirectivo(payload: {
  nombre_apellido: string;
}) {
  return http<Directivo>("/directivos/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function asignarDirectivo(payload: {
  id_directivo: number;
  id_grupo_utn: number;
  id_cargo: number;
  fecha_inicio: string;
}) {
  return http<{ message: string }>("/directivos/asignar", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getDirectivosActuales(grupoId: number) {
  return http<DirectivoActual[]>(`/directivos/grupo/${grupoId}/actuales`, {
    method: "GET",
  });
}

export function crearYAsignarDirectivo(payload: {
  nombre_apellido: string;
  id_grupo_utn: number;
  id_cargo: number;
  fecha_inicio: string;
}) {
  return http<Directivo>("/directivos/crear-y-asignar", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPeriodosDirectivos(grupoId: number) {
  return http<DirectivoPeriodo[]>(`/directivos/grupo/${grupoId}`, {
    method: "GET",
  });
}

export function getCambiosDirectivos(grupoId: number, page: number) {
  return http<CambiosDirectivosPage>(`/directivos/grupo/${grupoId}/cambios?page=${page}`);
}

export function updateDirectivo(
  directivoId: number,
  payload: UpdateDirectivoPayload
) {
  return http<{ message: string }>(`/directivos/${directivoId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function finalizarDirectivo(payload: FinalizarDirectivoPayload) {
  return http<{ message: string }>("/directivos/finalizar", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
