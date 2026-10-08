import { useQuery } from "@tanstack/react-query";
import {
  getArticulosDivulgacion,
  deleteArticulo,
  type ArticuloDivulgacion,
} from "@/modules/produccion/services/articulosDivulgacionServices";
import { useUct } from "@/modules/grupo/hooks/useUct";

export function useArticulosDivulgacion(
  activos: "true" | "false" | "all" = "true"
) {
  const { uct } = useUct();

  const query = useQuery<ArticuloDivulgacion[]>({
    queryKey: ["articulos-divulgacion", activos],
    queryFn: () =>
      getArticulosDivulgacion({
        grupo_utn_id: uct?.id,
        activos,
      }),
    enabled: !!uct,
    staleTime: 60_000,
  });

  return {
    list: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    remove: deleteArticulo,
  };
}
