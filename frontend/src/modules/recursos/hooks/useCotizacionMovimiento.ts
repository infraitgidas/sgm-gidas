import { useQuery } from "@tanstack/react-query";
import { getCotizacionMovimiento } from "@/modules/recursos/services/erogacionesServices";

export function useCotizacionMovimiento(fecha: string, enabled: boolean) {
  return useQuery({
    queryKey: ["cotizacion-movimiento", fecha],
    queryFn: () => getCotizacionMovimiento(fecha),
    enabled: enabled && Boolean(fecha),
  });
}
