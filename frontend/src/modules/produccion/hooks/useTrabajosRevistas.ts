import { useQuery } from "@tanstack/react-query";
import {
  getTrabajosRevistas,
  type TrabajoRevista,
} from "@/modules/produccion/services/trabajosRevistasServices";

export function useTrabajosRevistas(
  activos: "true" | "false" | "all" = "true",
  orden: "asc" | "desc" = "asc"
) {
  const query = useQuery<TrabajoRevista[]>({
    queryKey: ["trabajos-revistas", activos, orden],
    queryFn: () =>
      getTrabajosRevistas({
        activos,
        orden,
      }),
    staleTime: 60_000,
  });

  return {
    list: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
  };
}
