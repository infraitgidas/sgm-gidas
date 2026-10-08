import { useQuery } from "@tanstack/react-query";
import { getTiposRevista } from "@/modules/produccion/services/tipoRevistaServices";

export function useTiposRevista() {
  const query = useQuery({
    queryKey: ["tipos-revista"],
    queryFn: getTiposRevista,
  });

  return {
    tipos: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
