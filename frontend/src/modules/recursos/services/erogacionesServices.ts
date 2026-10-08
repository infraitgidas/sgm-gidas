import { http } from "@/lib/http";

const BASE = "/recursos/movimientos";

export type TipoMovimiento = "INGRESO" | "EGRESO";
export type MonedaMovimiento = "ARS" | "USD";

export type CategoriaErogacion = {
  id: number;
  codigo: "CORRIENTE" | "CAPITAL";
  nombre: string;
};

export type Erogacion = {
  id: number;
  numero_movimiento: number;
  tipo_movimiento: TipoMovimiento;
  monto: string;
  moneda: MonedaMovimiento;
  tipo_cambio_id: number | null;
  tipo_cambio_aplicado: string | null;
  monto_equivalente_ars: string | null;
  tipo_cambio: CotizacionMovimiento | null;
  fecha: string;
  grupo_utn_id: number;
  fuente_financiamiento_id: number | null;
  categoria_erogacion_id: number | null;
  equipamiento_id: number | null;
  fuente: { id: number; nombre: string } | null;
  categoria_erogacion: CategoriaErogacion | null;
  equipamiento: { id: number; denominacion: string } | null;
  grupo: { id: number; nombre: string } | null;
  activo: boolean;
  created_at: string | null;
  created_by: number | null;
  created_by_nombre?: string | null;
  updated_at: string | null;
  updated_by: number | null;
  updated_by_nombre?: string | null;
  deleted_at: string | null;
  deleted_by: number | null;
  deleted_by_nombre?: string | null;
};

export type Erogaciones = Erogacion;

export type CotizacionMovimiento = {
  id: number;
  fecha_cotizacion: string;
  valor: string;
  serie_bcra: number;
  fuente: string;
  moneda_origen: "USD";
  moneda_destino: "ARS";
};

export type HistorialErogacionItem = {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
};

export type ResumenFinanciero = {
  moneda: "ARS";
  saldo_disponible: string;
  total_ingresos: string;
  total_egresos: string;
  cantidad_movimientos: number;
};

export type SaldoPorFuente = {
  fuente_id: number;
  fuente_nombre: string;
  total_ingresos: string;
  total_egresos: string;
  saldo_disponible: string;
  cantidad_movimientos: number;
};

export type EquipamientoDisponible = {
  id: number;
  denominacion: string;
  monto_invertido: string;
};

export type CreateErogacionPayload = {
  tipo_movimiento: TipoMovimiento;
  moneda: MonedaMovimiento;
  monto: string;
  fecha: string;
  grupo_utn_id: number;
  fuente_financiamiento_id: number;
  categoria_erogacion_id?: number;
  equipamiento_id?: number;
};

export type UpdateErogacionPayload = Partial<Pick<
  CreateErogacionPayload,
  "monto" | "fecha" | "fuente_financiamiento_id" | "categoria_erogacion_id"
>>;
export type UpdateMovimientoPayload = UpdateErogacionPayload & { equipamiento_id?: number | null };

export async function getErogaciones(activos: "true" | "false" | "all" = "true", grupoId?: number) {
  const params = new URLSearchParams({ activos });
  if (grupoId) params.set("grupo_utn_id", String(grupoId));
  return http<Erogacion[]>(`${BASE}/?${params}`);
}

export async function getErogacionById(id: number) {
  return http<Erogacion>(`${BASE}/${id}`);
}

export async function getHistorialErogacionById(id: number) {
  return http<HistorialErogacionItem[]>(`${BASE}/${id}/historial`);
}

export async function getCategoriasErogacion() {
  return http<CategoriaErogacion[]>(`${BASE}/categorias`);
}

export async function getCotizacionMovimiento(fecha: string) {
  return http<CotizacionMovimiento>(`${BASE}/cotizacion?fecha=${encodeURIComponent(fecha)}`);
}

export async function getResumenFinanciero(grupoId: number) {
  return http<ResumenFinanciero>(`${BASE}/grupos/${grupoId}/resumen`);
}

export async function getSaldosPorFuente(grupoId: number) {
  return http<SaldoPorFuente[]>(`${BASE}/grupos/${grupoId}/saldos-por-fuente`);
}

export async function getEquipamientosDisponibles(grupoId: number, movimientoId?: number) {
  const params = movimientoId ? `?movimiento_id=${movimientoId}` : "";
  return http<EquipamientoDisponible[]>(`${BASE}/grupos/${grupoId}/equipamientos-disponibles${params}`);
}

export async function createErogacion(payload: CreateErogacionPayload) {
  return http<Erogacion>(`${BASE}/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateErogacion(id: number, payload: UpdateMovimientoPayload) {
  return http<Erogacion>(`${BASE}/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteErogaciones(id: number) {
  return http<{ message: string }>(`${BASE}/${id}`, { method: "DELETE" });
}
