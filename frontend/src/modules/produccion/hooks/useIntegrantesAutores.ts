import { useQuery } from "@tanstack/react-query";
import { getIntegrantesAutores } from "@/modules/produccion/services/trabajoAutoresServices";

export function useIntegrantesAutores() {
  return useQuery({ queryKey: ["integrantes-autores", "investigadores-becarios"], queryFn: getIntegrantesAutores });
}
