import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getBecasPage } from "@/modules/recursos/services/becasService";

export function useBecasPage(page: number, activos: "true" | "false" | "all", search: string) {
  return useQuery({
    queryKey: ["becas", "page", page, activos, search],
    queryFn: () => getBecasPage(page, activos, search),
    placeholderData: keepPreviousData,
  });
}
