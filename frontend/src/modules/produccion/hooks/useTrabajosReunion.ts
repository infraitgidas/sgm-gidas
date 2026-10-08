import { useQuery } from "@tanstack/react-query";
import {
  getTrabajosReunion,
  type TrabajoReunion,
} from "@/modules/produccion/services/trabajosReunionServices";

export function useTrabajosReunion(
  activos: "true" | "false" | "all" = "true",
  orden: "asc" | "desc" = "asc"
) {
  const { data, isLoading, isFetching, isError, refetch } = useQuery<TrabajoReunion[]>({
    queryKey: ["trabajos-reunion", activos, orden],
    queryFn: () =>
      getTrabajosReunion({
        activos,
        orden,
      }),
    staleTime: 60_000,
  });

  return {
    list: data ?? [],
    isLoading,
    isFetching,
    isError,
    refetch,
  };
}
