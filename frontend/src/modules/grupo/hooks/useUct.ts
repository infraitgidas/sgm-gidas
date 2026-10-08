import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteUct,
  getUct,
  getHistorialGrupo,
  upsertUct,
  type HistorialGrupoItem,
  type Uct,
} from "@/modules/grupo/services/uctServices";

type UctPayload = Partial<Omit<Uct, "id">>;

export function useUct() {
  const qc = useQueryClient();

  const uctQuery = useQuery<Uct | null>({
    queryKey: ["uct"],
    queryFn: getUct,
    staleTime: 60_000,
  });

  const saveMutation = useMutation({
    mutationFn: (data: UctPayload) => {
      if (uctQuery.data?.id) {
        return upsertUct(
          { ...data, id: uctQuery.data.id },
          true
        );
      }

      return upsertUct(data, false);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["uct"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUct,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["uct"] });
    },
  });

  return {
    uct: uctQuery.data ?? null,
    isLoading: uctQuery.isLoading,
    isError: uctQuery.isError,

    save: saveMutation.mutateAsync,
    saving: saveMutation.isPending,

    remove: deleteMutation.mutateAsync,
    removing: deleteMutation.isPending,
  };
}

export function useHistorialGrupo(grupoId?: number, enabled = false) {
  return useQuery<HistorialGrupoItem[]>({
    queryKey: ["grupo-utn-historial", grupoId],
    queryFn: () => getHistorialGrupo(grupoId as number),
    enabled: !!grupoId && enabled,
  });
}
