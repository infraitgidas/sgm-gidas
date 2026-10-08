import { useQuery } from "@tanstack/react-query";
import { getSaldosPorFuente } from "@/modules/recursos/services/erogacionesServices";

export function useSaldosPorFuente(grupoId?: number) {
  return useQuery({
    queryKey: ["saldos-por-fuente", grupoId],
    queryFn: () => getSaldosPorFuente(grupoId!),
    enabled: Boolean(grupoId),
  });
}
