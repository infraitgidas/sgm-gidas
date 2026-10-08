import { useQuery } from "@tanstack/react-query";
import { getErogaciones, type Erogacion } from "@/modules/recursos/services/erogacionesServices";

export function useErogaciones(
  activos: "true" | "false" | "all" = "true",
  grupoId?: number,
) {
  const { data = [], isLoading, isFetching, isError, refetch } = useQuery<Erogacion[]>({
    queryKey: ["erogaciones", activos, grupoId],
    queryFn: () => getErogaciones(activos, grupoId),
    enabled: Boolean(grupoId),
    staleTime: 60_000,
  });

  return { list: data, isLoading, isFetching, isError, refetch };
}
