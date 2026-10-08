import { keepPreviousData, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getProyectos,
  getProyectosPage,
  upsertProyectos,
  deleteProyectos,
  getProyectoById,
  cerrarProyecto,
  reabrirProyecto,
  vincularInvestigadores,
  vincularBecarios,
  desvincularInvestigadores,
  desvincularBecarios,
  type Proyecto,
  type InvestigadorVinculacionPayload,
  type ProyectosActivosFilter,
  type ProyectoListParams,
} from "@/modules/proyectos/services/proyectosServices";

const QUERY_KEY = ["proyectos"];

/* =========================
   GET ALL
========================= */
export function useProyectos(activos: ProyectosActivosFilter = "true") {
  return useQuery({
    queryKey: [...QUERY_KEY, activos],
    queryFn: () => getProyectos(activos),
    staleTime: 60_000,
  });
}

/* =========================
   GET BY ID
========================= */
export function useProyecto(id?: string) {
  return useQuery({
    queryKey: ["proyecto", id],
    queryFn: () => (id ? getProyectoById(Number(id)) : null),
    enabled: Boolean(id),
  });
}

/* =========================
   UPSERT (CREATE / UPDATE)
========================= */
export function useUpsertProyecto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Proyecto) => upsertProyectos(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });

      if (variables.id) {
        queryClient.invalidateQueries({
          queryKey: ["proyecto", String(variables.id)],
        });
      }
    },
  });
}

/* =========================
   DELETE
========================= */
export function useDeleteProyecto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteProyectos(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: ["proyecto", String(id)],
      });
    },
  });
}

/* =========================
   CERRAR PROYECTO
========================= */
export function useCerrarProyecto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      fechaFin,
    }: {
      id: string;
      fechaFin: string;
    }) => cerrarProyecto(id, fechaFin),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: ["proyecto", String(variables.id)],
      });
    },
  });
}

/* =========================
   REABRIR PROYECTO
========================= */
export function useReabrirProyecto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => reabrirProyecto(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: ["proyecto", String(id)],
      });
    },
  });
}

/* =========================
   VINCULAR INVESTIGADORES
========================= */
export function useVincularInvestigadores() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      proyectoId,
      investigadores,
    }: {
      proyectoId: number;
      investigadores: InvestigadorVinculacionPayload[];
    }) => vincularInvestigadores(proyectoId, investigadores),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: ["proyecto", String(variables.proyectoId)],
      });
    },
  });
}

/* =========================
   VINCULAR BECARIOS
========================= */
export function useVincularBecarios() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      proyectoId,
      becariosIds,
      fechaInicio,
    }: {
      proyectoId: number;
      becariosIds: number[];
      fechaInicio: string;
    }) => vincularBecarios(proyectoId, becariosIds, fechaInicio),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: ["proyecto", String(variables.proyectoId)],
      });
    },
  });
}

/* =========================
   DESVINCULAR INVESTIGADORES
========================= */
export function useDesvincularInvestigadores() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      proyectoId,
      fechaFin,
      investigadoresIds,
    }: {
      proyectoId: number;
      fechaFin: string;
      investigadoresIds: number[];
    }) =>
      desvincularInvestigadores(
        proyectoId,
        fechaFin,
        investigadoresIds
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: ["proyecto", String(variables.proyectoId)],
      });
    },
  });
}

/* =========================
   DESVINCULAR BECARIOS
========================= */
export function useDesvincularBecarios() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      proyectoId,
      fechaFin,
      becariosIds,
    }: {
      proyectoId: number;
      fechaFin: string;
      becariosIds: number[];
    }) => desvincularBecarios(proyectoId, fechaFin, becariosIds),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({
        queryKey: ["proyecto", String(variables.proyectoId)],
      });
    },
  });
}

export function useProyectosPage(params: ProyectoListParams) {
  const query = useQuery({
    queryKey: [...QUERY_KEY, "page", params],
    queryFn: () => getProyectosPage(params),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });

  return {
    ...query,
    list: query.data?.data ?? [],
    meta: query.data?.meta ?? {
      page: params.page,
      per_page: params.perPage ?? 9,
      total: 0,
      total_pages: 0,
    },
  };
}
