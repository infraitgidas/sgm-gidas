import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getEquipamiento,
  createEquipamiento,
  updateEquipamiento,
  deleteEquipamiento,
  type Equipamiento,
} from "@/modules/recursos/services/equipamientoServices";
import { getUct } from "@/modules/grupo/services/uctServices";

export function useEquipamiento(
  activos: "true" | "false" | "all" = "true"
) {
  const qc = useQueryClient();

  const equipamientoQuery = useQuery({
    queryKey: ["equipamiento", activos],
    queryFn: () => getEquipamiento(activos),
    staleTime: 60_000,
  });

  const uctQuery = useQuery({
    queryKey: ["uct"],
    queryFn: getUct,
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: async (
      data: Omit<Equipamiento, "id" | "created_by" | "created_at" | "deleted_by" | "deleted_at" | "grupo_utn_id">
    ) => {
      if (!uctQuery.data?.id) {
        throw new Error("No hay grupo UTN configurado");
      }

      return createEquipamiento({
        ...data,
        grupo_utn_id: uctQuery.data.id,
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipamiento"] }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Equipamiento> }) =>
      updateEquipamiento(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipamiento"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteEquipamiento,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["equipamiento"] }),
  });

  return {
    list: equipamientoQuery.data ?? [],
    isLoading: equipamientoQuery.isLoading,
    isFetching: equipamientoQuery.isFetching,
    isError: equipamientoQuery.isError,
    refetch: equipamientoQuery.refetch,

    create: createMutation.mutateAsync,
    creating: createMutation.isPending,

    update: updateMutation.mutateAsync,
    updating: updateMutation.isPending,

    remove: deleteMutation.mutateAsync,
    removing: deleteMutation.isPending,
  };
}
