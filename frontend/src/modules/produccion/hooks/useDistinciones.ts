import { useMutation, useQuery } from "@tanstack/react-query";
import {
  eliminarDistincion,
  getDistinciones,
  type Distincion,
} from "@/modules/produccion/services/distincionesServices";

export function useDistinciones(
  activos: "true" | "false" | "all" = "true"
) {
  const query = useQuery<Distincion[]>({
    queryKey: ["distinciones", activos],
    queryFn: () =>
      getDistinciones({
        activos,
        orden: "asc",
      }),
    staleTime: 60_000,
  });

  const remove = useMutation({
    mutationFn: (id: number) => eliminarDistincion(id),
  });

  return {
    list: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    remove: remove.mutateAsync,
    isRemoving: remove.isPending,
  };
}
