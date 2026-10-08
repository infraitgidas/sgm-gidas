import { useQuery } from "@tanstack/react-query";
import { esPrimerUsuario } from "@/modules/auth/services/authService";

export const SYSTEM_SETUP_QUERY_KEY = ["system-setup"] as const;

export function useSystemSetup(enabled = true) {
  return useQuery({
    queryKey: SYSTEM_SETUP_QUERY_KEY,
    queryFn: esPrimerUsuario,
    enabled,
    retry: false,
  });
}
