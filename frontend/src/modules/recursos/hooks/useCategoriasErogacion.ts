import { useQuery } from "@tanstack/react-query";
import { getCategoriasErogacion } from "@/modules/recursos/services/erogacionesServices";

export function useCategoriasErogacion() {
  return useQuery({
    queryKey: ["categorias-erogacion"],
    queryFn: getCategoriasErogacion,
    staleTime: 5 * 60_000,
  });
}
