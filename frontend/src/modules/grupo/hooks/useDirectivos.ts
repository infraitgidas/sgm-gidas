import { useMutation, useQuery } from "@tanstack/react-query";
import {
  crearYAsignarDirectivo,
  finalizarDirectivo,
  getDirectivosActuales,
  getPeriodosDirectivos,
  getCambiosDirectivos,
  updateDirectivo,
  type DirectivoActual,
  type DirectivoPeriodo,
  type CambiosDirectivosPage,
} from "@/modules/grupo/services/directivosServices";

export function useDirectivos(grupoId?: number, enabled = true) {
  return useQuery<DirectivoActual[]>({
    queryKey: ["directivos-actuales", grupoId],
    queryFn: () => getDirectivosActuales(grupoId as number),
    enabled: enabled && !!grupoId,
  });
}

export function usePeriodosDirectivos(grupoId?: number, enabled = false) {
  return useQuery<DirectivoPeriodo[]>({
    queryKey: ["directivos-periodos", grupoId],
    queryFn: () => getPeriodosDirectivos(grupoId as number),
    enabled: !!grupoId && enabled,
  });
}

export function useCambiosDirectivos(grupoId?: number, page = 1, enabled = false) {
  return useQuery<CambiosDirectivosPage>({
    queryKey: ["directivos-cambios", grupoId, page],
    queryFn: () => getCambiosDirectivos(grupoId as number, page),
    enabled: !!grupoId && enabled,
    placeholderData: (previous) => previous,
  });
}

export function useCrearYAsignarDirectivo(grupoId: number) {
  return useMutation({
    mutationFn: async (payload: {
      nombre_apellido: string;
      id_cargo: number;
      fecha_inicio: string;
    }) => {
      const directivo = await crearYAsignarDirectivo({
        nombre_apellido: payload.nombre_apellido,
        id_grupo_utn: grupoId,
        id_cargo: payload.id_cargo,
        fecha_inicio: payload.fecha_inicio,
      });

      return directivo;
    },
  });
}

export function useActualizarDirectivo(grupoId?: number) {
  return useMutation({
    mutationFn: ({
      id,
      nombre_apellido,
    }: {
      id: number;
      nombre_apellido: string;
    }) => updateDirectivo(id, { nombre_apellido }),
  });
}

export function useFinalizarDirectivo(grupoId?: number) {
  return useMutation({
    mutationFn: ({
      id_directivo,
      fecha_fin,
    }: {
      id_directivo: number;
      fecha_fin: string;
    }) =>
      finalizarDirectivo({
        id_directivo,
        fecha_fin,
        id_grupo_utn: grupoId as number,
      }),
  });
}
