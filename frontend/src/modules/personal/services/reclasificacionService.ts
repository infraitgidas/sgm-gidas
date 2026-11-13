import { http } from "@/lib/http";
import type { PersonalCompleto } from "./personalCompletoServices";

export type ClasePersonal = "personal" | "becario" | "investigador";
export type ReclasificarFormulario = (payload: Record<string, unknown>) => Promise<PersonalCompleto>;

export function reclasificarPersonal(rol: string, id: number, clase: ClasePersonal, cambios: Record<string, unknown>) {
  return http<PersonalCompleto>(`/personal/${rol}/${id}/reclasificar`, {
    method: "PUT",
    body: JSON.stringify({ ...cambios, clase_destino: clase }),
  });
}
