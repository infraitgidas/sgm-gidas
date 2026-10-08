import { http } from "@/lib/http";

export interface InvestigadorPayload {
  nombre_apellido: string;
  dni: string;
  cuil: string;
  horas_semanales: number;
  fecha_alta_grupo: string;
  created_by?: number | null;
  deleted_by?: number | null;
  created_at?: string | null | undefined;
  deleted_at?: string | null | undefined;
  grupo_utn_id: number;
  tipo_dedicacion_id: number;   // 🔥 CORREGIDO
  categoria_utn_id?: number | null;
  programa_incentivos_id?: number | null;
  activo: boolean;
}

export interface Investigador extends InvestigadorPayload {
  id: number;
}

export function crearInvestigador(payload: InvestigadorPayload) {
  return http<Investigador>("/investigadores/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function actualizarInvestigador(
  id: number,
  payload: Partial<InvestigadorPayload>,
  rol: string
) {
  return http<Investigador>(`/personal/${rol}/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}


export function getInvestigadorById(id: number) {
  return http<Investigador>(`/investigadores/${id}`, {
    method: "GET",
  });
}

export function getInvestigadores() {
  return http<Investigador[]>("/investigadores/", {
    method: "GET",
  });
}
