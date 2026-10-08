import { useQuery } from "@tanstack/react-query";
import { getTiposPersonal } from "@/modules/catalogos/services/tiposServices";

export function useTiposPersonal() {
  return useQuery({
    queryKey: ["tipo-personal"],
    queryFn: getTiposPersonal,
    staleTime: 0,
    refetchOnMount: "always",
  });
}
