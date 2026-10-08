import { http } from "@/lib/http";

export type DashboardResumenParams = {
  anios?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  solo_becarios_con_beca_activa?: boolean;
};

export type DashboardResumen = {
  total_proyectos: number;
  proyectos_activos: number;
  proyectos_finalizados: number;
  total_investigadores: number;
  investigadores_con_proyectos_activos: number;
  total_becarios: number;
  becarios_con_proyectos_activos: number;
  total_personal: number;
  total_grupos: number;
  total_becas: number;
  total_erogaciones: number;
  total_ingresos: string;
  total_egresos: string;
  saldo_financiero: string;
  egresos_corrientes: string;
  egresos_capital: string;
  total_transferencias: number;
  total_fuentes_financiamiento: number;
  monto_total_proyectos: number;
  promedio_monto_proyecto: number;
};

export type ProyectoPorTipo = {
  tipo: string;
  total: number;
};

export type ProyectoPorFuente = {
  fuente: string;
  total: number;
};

export type ProyectoPorDistincion = {
  categoria: string;
  total: number;
};

export type ErogacionPorTipo = {
  tipo: string;
  total_registros: number;
  total_egresos: number;
  total_ingresos: number;
  balance: number;
};

export type TransferenciaPorTipoContrato = {
  tipo_contrato: string;
  total: number;
  monto_total: number;
};

export type BecarioPorTipoFormacion = {
  tipo_formacion: string;
  total: number;
};

export type IntegrantesPorGrupo = {
  grupo_id: number;
  grupo: string;
  unidad_academica: string;
  investigadores: number;
  becarios: number;
  personal: number;
  total_integrantes: number;
  proyectos_activos: number;
};

export type SerieAnual = {
  anio: number;
  total: number;
};

export type ProyectoPorVencer = {
  id: number;
  codigo_proyecto: string;
  nombre_proyecto: string;
  fecha_fin: string;
  dias_restantes: number;
  grupo: string | null;
};

export type DashboardResumenResponse = {
  generado_en: string;
  parametros: {
    anios: number;
    fecha_desde: string | null;
    fecha_hasta: string | null;
    solo_becarios_con_beca_activa: boolean;
  };
  resumen: DashboardResumen;
  distribuciones: {
    proyectos_por_tipo: ProyectoPorTipo[];
    proyectos_por_fuente: ProyectoPorFuente[];
    proyectos_por_distinciones: ProyectoPorDistincion[];
    erogaciones_por_tipo: ErogacionPorTipo[];
    transferencias_por_tipo_contrato: TransferenciaPorTipoContrato[];
    becarios_por_tipo_formacion: BecarioPorTipoFormacion[];
    integrantes_por_grupo: IntegrantesPorGrupo[];
  };
  series: {
    proyectos_por_anio_inicio: SerieAnual[];
    proyectos_finalizados_por_anio: SerieAnual[];
    monto_proyectos_por_anio_inicio: SerieAnual[];
  };
  alertas: {
    proyectos_sin_financiamiento: number;
    proyectos_sin_grupo: number;
    proyectos_por_vencer: ProyectoPorVencer[];
  };
};

function buildDashboardResumenQuery(params?: DashboardResumenParams) {
  if (!params) return "";

  if (
    params.anios !== undefined &&
    (!Number.isInteger(params.anios) || params.anios <= 0)
  ) {
    throw new Error("La cantidad de anos debe ser un entero mayor a cero.");
  }

  if (
    params.fecha_desde &&
    params.fecha_hasta &&
    params.fecha_desde > params.fecha_hasta
  ) {
    throw new Error("La fecha desde no puede ser posterior a la fecha hasta.");
  }

  const searchParams = new URLSearchParams();

  if (params.anios !== undefined) {
    searchParams.set("anios", String(params.anios));
  }

  if (params.fecha_desde) {
    searchParams.set("fecha_desde", params.fecha_desde);
  }

  if (params.fecha_hasta) {
    searchParams.set("fecha_hasta", params.fecha_hasta);
  }

  if (params.solo_becarios_con_beca_activa !== undefined) {
    searchParams.set(
      "solo_becarios_con_beca_activa",
      String(params.solo_becarios_con_beca_activa)
    );
  }

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function getDashboardResumen(
  params?: DashboardResumenParams
): Promise<DashboardResumenResponse> {
  const query = buildDashboardResumenQuery(params);

  return http<DashboardResumenResponse>(`/dashboards/resumen${query}`, {
    method: "GET",
  });
}
