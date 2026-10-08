import { useQuery } from "@tanstack/react-query";

import {
  eliminarParticipacion,
  getParticipaciones,
  type Participacion,
} from "@/modules/proyectos/services/participacionesServices";

export function useParticipaciones(activos: "true" | "false" | "all" = "true") {
  const query = useQuery<Participacion[]>({
    queryKey: ["participaciones", activos],
    queryFn: () => getParticipaciones({ activos, orden: "desc" }),
    staleTime: 60_000,
  });

  return {
    list: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    remove: eliminarParticipacion,
  };
}
