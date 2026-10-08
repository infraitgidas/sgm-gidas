import { http } from "@/lib/http";

export type ProyectosActivosFilter = "true" | "false" | "all";
export type ProyectoSort =
  | "codigo"
  | "nombre"
  | "tipo"
  | "fuente"
  | "fecha_inicio"
  | "fecha_fin"
  | "estado";

export type ProyectoListParams = {
  page: number;
  perPage?: number;
  search?: string;
  activos?: ProyectosActivosFilter;
  sort?: ProyectoSort;
  direction?: "asc" | "desc";
  tipoProyectoId?: number;
  fuenteFinanciamientoId?: number;
  investigadorId?: number;
  becarioId?: number;
  ids?: Array<number | string>;
};

export type InvestigadorProyecto = {
  activo?: boolean;
  fecha_inicio: string;
  fecha_fin?: string | null;
  id: number;
  nombre_apellido: string;
  es_coordinador?: boolean;
};

export type BecarioProyecto = {
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
  id: number;
  nombre_apellido: string;
};

export type InvestigadorVinculacionPayload = {
  id_investigador: number;
  fecha_inicio: string;
  fecha_fin?: string | null;
  es_coordinador?: boolean;
};

export type HistorialProyectoItem = {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
};

export type Proyecto = {
  id?: string;
  created_by?: number | null;
  created_by_nombre?: string | null;
  created_at?: string | null | undefined;
  updated_by?: number | null;
  updated_by_nombre?: string | null;
  updated_at?: string | null | undefined;
  deleted_by?: number | null;
  deleted_by_nombre?: string | null;
  deleted_at?: string | null | undefined;
  activo?: boolean;
  cerrado?: boolean;
  tipoProyectoId: number;
  tipoProyectoNombre?: string;
  codigoProyecto: string;
  nombreProyecto: string;
  fechaInicio: string;
  fechaFinalizacion?: string | null;
  fechaFinOriginal?: string | null;
  fechaFinProrrogada?: string | null;
  prorrogaMotivo?: string | null;
  prorrogaByNombre?: string | null;
  prorrogaAt?: string | null;
  fuenteFinanciamientoId?: number | null;
  fuenteFinanciamientoNombre?: string;
  descripcionProyecto?: string;
  logrosObtenidos?: string;
  dificultadesProyecto?: string;
  montoDestinado?: number;
  grupoUtnId?: number | null;
  grupoUtnNombre?: string;
  investigadores?: InvestigadorProyecto[];
  becarios?: BecarioProyecto[];
};

export type ProyectoPayload = {
  investigadoresIds?: number[];
  becariosIds?: number[];
  coordinadorId?: number | null;
  id?: string;
  codigoProyecto?: string;
  nombreProyecto?: string;
  fechaInicio?: string;
  fechaFinalizacion?: string | null;
  tipoProyectoId?: number | null;
  fuenteFinanciamientoId?: number | null;
  descripcionProyecto?: string;
  logrosObtenidos?: string;
  dificultadesProyecto?: string;
  montoDestinado?: number | null;
  grupoUtnId?: number | null;
};

type ProyectoApiResponse = {
  id: number | string;
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
  cerrado?: boolean;
  codigo_proyecto: string;
  nombre_proyecto: string;
  descripcion_proyecto?: string | null;
  logros_obtenidos?: string | null;
  dificultades_proyecto?: string | null;
  monto_destinado?: string | number | null;
  fecha_inicio: string;
  fecha_fin?: string | null;
  fecha_fin_original?: string | null;
  fecha_fin_prorrogada?: string | null;
  prorroga_motivo?: string | null;
  prorroga_by_nombre?: string | null;
  prorroga_at?: string | null;
  tipo_proyecto_id: number;
  tipo_proyecto?: { id: number; nombre?: string | null } | null;
  fuente_financiamiento_id?: number | null;
  fuente_financiamiento?: { id: number; nombre?: string | null } | null;
  grupo_utn_id?: number | null;
  grupo_utn?: { id: number; nombre?: string | null; nombre_sigla_grupo?: string | null } | null;
  investigadores?: InvestigadorProyecto[];
  becarios?: BecarioProyecto[];
};

export type ProyectoPage = {
  data: ProyectoApiResponse[];
  meta: { page: number; per_page: number; total: number; total_pages: number };
  error: null;
};

function mapProyecto(p: ProyectoApiResponse): Proyecto {
  return {
    id: String(p.id),
    created_by: p.created_by ?? null,
    created_by_nombre: p.created_by_nombre ?? null,
    created_at: p.created_at ?? null,
    updated_by: p.updated_by ?? null,
    updated_by_nombre: p.updated_by_nombre ?? null,
    updated_at: p.updated_at ?? null,
    deleted_by: p.deleted_by ?? null,
    deleted_by_nombre: p.deleted_by_nombre ?? null,
    deleted_at: p.deleted_at ?? null,
    activo: p.activo,
    cerrado: Boolean(p.cerrado),
    codigoProyecto: String(p.codigo_proyecto),
    nombreProyecto: p.nombre_proyecto,
    descripcionProyecto: p.descripcion_proyecto || "",
    logrosObtenidos: p.logros_obtenidos || "",
    dificultadesProyecto: p.dificultades_proyecto || "",
    montoDestinado:
      p.monto_destinado !== null && p.monto_destinado !== undefined
        ? Number(p.monto_destinado)
        : undefined,
    fechaInicio: p.fecha_inicio,
    fechaFinalizacion: p.fecha_fin,
    fechaFinOriginal: p.fecha_fin_original,
    fechaFinProrrogada: p.fecha_fin_prorrogada,
    prorrogaMotivo: p.prorroga_motivo,
    prorrogaByNombre: p.prorroga_by_nombre,
    prorrogaAt: p.prorroga_at,
    tipoProyectoId: p.tipo_proyecto?.id ?? p.tipo_proyecto_id,
    tipoProyectoNombre: p.tipo_proyecto?.nombre || "N/A",
    fuenteFinanciamientoId:
      p.fuente_financiamiento?.id ?? p.fuente_financiamiento_id ?? null,
    fuenteFinanciamientoNombre: p.fuente_financiamiento?.nombre || "N/A",
    grupoUtnId: p.grupo_utn?.id ?? p.grupo_utn_id ?? null,
    grupoUtnNombre:
      p.grupo_utn?.nombre || p.grupo_utn?.nombre_sigla_grupo || undefined,
    investigadores: (p.investigadores || []).map((inv) => ({
      id: inv.id,
      nombre_apellido: inv.nombre_apellido,
      fecha_inicio: inv.fecha_inicio,
      fecha_fin: inv.fecha_fin,
      es_coordinador: Boolean(inv.es_coordinador),
      activo: inv.activo,
    })),
    becarios: (p.becarios || []).map((bec) => ({
      id: bec.id,
      nombre_apellido: bec.nombre_apellido,
      fecha_inicio: bec.fecha_inicio,
      fecha_fin: bec.fecha_fin,
    })),
  };
}

export async function getProyectos(
  activos: ProyectosActivosFilter = "true"
): Promise<Proyecto[]> {
  const activosParam =
    activos === "all" || activos === "false" || activos === "true"
      ? activos
      : "true";

  const data = await http<ProyectoApiResponse[]>(`/proyectos?activos=${activosParam}`);
  return data.map(mapProyecto);
}

export async function getProyectosPage(
  params: ProyectoListParams
): Promise<{ data: Proyecto[]; meta: ProyectoPage["meta"]; error: null }> {
  const query = new URLSearchParams({
    page: String(params.page),
    per_page: String(params.perPage ?? 9),
    activos: params.activos ?? "true",
    sort: params.sort ?? "fecha_inicio",
    direction: params.direction ?? "desc",
  });
  if (params.search?.trim()) query.set("search", params.search.trim());
  if (params.tipoProyectoId) query.set("tipo_proyecto_id", String(params.tipoProyectoId));
  if (params.fuenteFinanciamientoId) query.set("fuente_financiamiento_id", String(params.fuenteFinanciamientoId));
  if (params.investigadorId) query.set("investigador_id", String(params.investigadorId));
  if (params.becarioId) query.set("becario_id", String(params.becarioId));
  if (params.ids) query.set("ids", params.ids.join(","));

  const response = await http<ProyectoPage>(`/proyectos?${query.toString()}`);
  return {
    data: response.data.map(mapProyecto),
    meta: response.meta,
    error: null,
  };
}

export async function upsertProyectos(payload: ProyectoPayload): Promise<Proyecto> {
  const body: Record<string, unknown> = {};
  if ("investigadoresIds" in payload) body.investigadores_ids = payload.investigadoresIds;
  if ("becariosIds" in payload) body.becarios_ids = payload.becariosIds;
  if ("coordinadorId" in payload) body.coordinador_id = payload.coordinadorId;

  if ("codigoProyecto" in payload) {
    body.codigo_proyecto = payload.codigoProyecto;
  }

  if ("nombreProyecto" in payload) {
    body.nombre_proyecto = payload.nombreProyecto;
  }

  if ("descripcionProyecto" in payload) {
    body.descripcion_proyecto = payload.descripcionProyecto;
  }

  if ("fechaInicio" in payload) {
    body.fecha_inicio = payload.fechaInicio;
  }

  if ("fechaFinalizacion" in payload) {
    body.fecha_fin = payload.fechaFinalizacion || null;
  }

  if ("logrosObtenidos" in payload) {
    body.logros_obtenidos = payload.logrosObtenidos?.trim() || null;
  }
  if ("dificultadesProyecto" in payload) {
    body.dificultades_proyecto = payload.dificultadesProyecto || null;
  }

  if ("montoDestinado" in payload) {
    body.monto_destinado =
      payload.montoDestinado !== undefined &&
      payload.montoDestinado !== null
        ? Number(payload.montoDestinado)
        : null;
  }

  if ("tipoProyectoId" in payload) {
    body.tipo_proyecto_id = payload.tipoProyectoId;
  }

  if ("fuenteFinanciamientoId" in payload) {
    body.fuente_financiamiento_id = payload.fuenteFinanciamientoId ?? null;
  }

  if ("grupoUtnId" in payload) {
    body.grupo_utn_id = payload.grupoUtnId ?? null;
  }

  const url = payload.id ? `/proyectos/${payload.id}` : "/proyectos";
  const method = payload.id ? "PUT" : "POST";

  const response = await http<ProyectoApiResponse>(url, {
    method,
    body: JSON.stringify(body),
  });
  return mapProyecto(response);
}

export async function deleteProyectos(id: string) {
  return http<void>(`/proyectos/${id}`, { method: "DELETE" });
}

export async function getProyectoById(id: number): Promise<Proyecto> {
  const data = await http<ProyectoApiResponse>(`/proyectos/${id}`);
  return mapProyecto(data);
}

export async function getHistorialProyectoById(
  id: number
): Promise<HistorialProyectoItem[]> {
  const data = await http<HistorialProyectoItem[] | { data?: HistorialProyectoItem[] }>(
    `/proyectos/${id}/historial`,
    {
      method: "GET",
    }
  );

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  return [];
}

export async function cerrarProyecto(id: string, fechaFin: string) {
  return http(`/proyectos/${id}/cerrar`, {
    method: "POST",
    body: JSON.stringify({
      fecha_fin: fechaFin,
    }),
  });
}

export async function reabrirProyecto(id: string) {
  return http(`/proyectos/${id}/reabrir`, {
    method: "PUT",
  });
}

export async function prorrogarProyecto(id: string, motivo: string): Promise<Proyecto> {
  const response = await http<ProyectoApiResponse>(`/proyectos/${id}/prorroga`, {
    method: "POST",
    body: JSON.stringify({ motivo }),
  });
  return mapProyecto(response);
}

export function vincularInvestigadores(
  proyectoId: number,
  investigadores: InvestigadorVinculacionPayload[]
) {
  return http(`/proyectos/${proyectoId}/investigadores`, {
    method: "POST",
    body: JSON.stringify(
      investigadores.map((inv) => ({
        id_investigador: inv.id_investigador,
        fecha_inicio: inv.fecha_inicio,
        fecha_fin: inv.fecha_fin ?? null,
        es_coordinador: Boolean(inv.es_coordinador),
      }))
    ),
  });
}

export function vincularBecarios(
  proyectoId: number,
  becariosIds: number[],
  fechaInicio: string
) {
  return http(`/proyectos/${proyectoId}/becarios`, {
    method: "POST",
    body: JSON.stringify(
      becariosIds.map((id) => ({
        id_becario: id,
        fecha_inicio: fechaInicio,
      }))
    ),
  });
}

export function desvincularInvestigadores(
  proyectoId: number,
  fechaFin: string,
  investigadoresIds: number[]
) {
  return http(`/proyectos/${proyectoId}/investigadores`, {
    method: "PUT",
    body: JSON.stringify(
      investigadoresIds.map((id) => ({
        id_investigador: id,
        fecha_fin: fechaFin,
      }))
    ),
  });
}

export function desvincularBecarios(
  proyectoId: number,
  fechaFin: string,
  becariosIds: number[]
) {
  return http(`/proyectos/${proyectoId}/becarios`, {
    method: "PUT",
    body: JSON.stringify(
      becariosIds.map((id) => ({
        id_becario: id,
        fecha_fin: fechaFin,
      }))
    ),
  });
}
