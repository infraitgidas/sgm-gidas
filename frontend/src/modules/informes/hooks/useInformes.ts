import { useQuery } from "@tanstack/react-query";
import { getInforme, getInformeCandidates, getInformeHistorial, getInformes, type InformeTipo } from "@/modules/informes/services/informesService";

export function useInformes(tipo: InformeTipo, page: number, memoriaId?: number) {
  return useQuery({ queryKey: ["informes", tipo, page, memoriaId], queryFn: () => getInformes(tipo, page, memoriaId) });
}
export function useInforme(tipo: InformeTipo, id?: number) {
  return useQuery({ queryKey: ["informe", tipo, id], queryFn: () => getInforme(tipo, id!), enabled: !!id });
}
export function useInformeHistorial(tipo: InformeTipo, id?: number) {
  return useQuery({ queryKey: ["informe-historial", tipo, id], queryFn: () => getInformeHistorial(tipo, id!), enabled: !!id });
}
export function useInformeCandidates(tipo: InformeTipo, memoriaId: number, search: string, page: number) {
  return useQuery({ queryKey: ["informe-candidatos", tipo, memoriaId, search, page], queryFn: () => getInformeCandidates(tipo, memoriaId, search, page), enabled: tipo !== "uct" && memoriaId > 0 });
}
