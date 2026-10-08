import { http } from "@/lib/http";

export interface HistorialHorasItem {
  id: number;
  horas_semanales: number;
  fecha_inicio: string;
  fecha_fin: string | null;
}

export interface HistorialCambioItem {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
  [key: string]: unknown;
}

type CatalogoRelacionado = { id?: number; nombre?: string };
type ColeccionRelacionada = Array<{
  nombre_apellido?: string;
  nombre?: string;
  titulo?: string;
}>;

export interface RelacionesPersonal {
  tipo_personal?: CatalogoRelacionado;
  tipo_formacion?: CatalogoRelacionado;
  categoria_utn?: CatalogoRelacionado;
  programa_incentivos?: CatalogoRelacionado;
  tipo_dedicacion?: CatalogoRelacionado;
  proyectos?: ColeccionRelacionada;
  actividades_docencia?: ColeccionRelacionada;
  trabajos_reunion_cientifica?: ColeccionRelacionada;
  participaciones_relevantes?: ColeccionRelacionada;
}

export interface PersonalCompleto {
  id: number;
  nombre_apellido: string;
  dni: string | null;
  cuil: string | null;
  created_by: number | null;
  created_at: string | null | undefined;
  updated_at?: string | null;
  deleted_by: number | null;
  deleted_at: string | null | undefined;
  updated_by_nombre?: string | null;
  fecha_alta_grupo?: string | null;
  horas_semanales: number;
  historial_horas?: HistorialHorasItem[];
  activo: boolean;
  tipo_personal_id?: number;
  tipo_formacion_id?: number;
  tipo_dedicacion_id?: number;
  categoria_utn_id?: number | null;
  programa_incentivos_id?: number | null;
  grupo_utn_id?: number;
  rol: "personal" | "becario" | "investigador" | "profesional";
  grupo?: {
    id: number;
    nombre: string;
  } | null;
  relaciones?: RelacionesPersonal;
  becas?: Array<{
    id: number;
    nombre_beca?: string;
    descripcion?: string;
    fecha_inicio?: string | null;
    fecha_fin?: string | null;
    monto_percibido?: number | null;
  }>;
}

export const getPersonalCompletoByRolAndId = (
  rol: string,
  id: number
) => {
  return http<PersonalCompleto>(`/personal/${rol}/${id}`);
};

export function getPersonalCompletoById(id: number) {
  return http<PersonalCompleto>(`/personal-all/${id}`);
}

export function getHistorialPersonalByRolAndId(
  rol: string,
  id: number
) {
  return http<HistorialCambioItem[]>(`/personal/${rol}/${id}/historial`);
}
