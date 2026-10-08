import type { Erogacion, HistorialErogacionItem } from "@/modules/recursos/services/erogacionesServices";

export function formatMovimientoMoney(value: string | number, moneda = "ARS") {
  const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(String(value));
  if (!match) return "—";
  const integer = new Intl.NumberFormat("es-AR").format(BigInt(match[2]));
  return `${match[1]}${moneda} ${integer},${(match[3] ?? "").padEnd(2, "0")}`;
}

export function presentMovimientoHistoryItems(items: HistorialErogacionItem[]) {
  return items.filter((item) => {
    const field = item.campo?.toLocaleLowerCase("es") ?? "";
    return field !== "accion" && field !== "acciones"
      && item.valor_anterior !== null && item.valor_anterior !== undefined
      && item.valor_anterior !== item.valor_nuevo;
  });
}

function readableValue(item: HistorialErogacionItem, value: unknown, movement: Erogacion): string {
  if (value === null || value === undefined || value === "") return "—";
  if (item.campo === "monto") return formatMovimientoMoney(String(value), movement.moneda);
  if (item.campo === "fecha") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
    return match ? `${match[3]}/${match[2]}/${match[1]}` : "Fecha no disponible";
  }
  if (item.campo === "tipo_movimiento") return value === "INGRESO" ? "Ingreso" : value === "EGRESO" ? "Egreso" : "—";
  if (item.campo === "activo") return value === true || value === "true" ? "Activo" : "Inactivo";
  if (item.campo === "fuente_financiamiento_id") return Number(value) === movement.fuente?.id ? movement.fuente.nombre : "Otra fuente de financiamiento";
  if (item.campo === "equipamiento_id") return Number(value) === movement.equipamiento?.id ? movement.equipamiento.denominacion : "Otro equipamiento";
  if (item.campo === "categoria_erogacion_id") return Number(value) === movement.categoria_erogacion?.id ? movement.categoria_erogacion.nombre : "Otra categoría de erogación";
  if (item.campo?.endsWith("_id")) return "Valor relacionado actualizado";
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const name = record.nombre ?? record.label ?? record.detalle;
    return typeof name === "string" && name.trim() ? name : "Valor anterior no disponible";
  }
  return String(value);
}

const fieldLabels: Record<string, string> = {
  monto: "Monto", fecha: "Fecha", tipo_movimiento: "Tipo de movimiento",
  fuente_financiamiento_id: "Fuente de financiamiento",
  equipamiento_id: "Equipamiento relacionado",
  categoria_erogacion_id: "Categoría de erogación", activo: "Estado",
};

export function formatMovimientoHistoryEntry(item: HistorialErogacionItem, movement: Erogacion) {
  const title = fieldLabels[item.campo ?? ""] ?? "Cambio del movimiento";
  return {
    title,
    description: `Anterior: ${readableValue(item, item.valor_anterior, movement)} · Nuevo: ${readableValue(item, item.valor_nuevo, movement)}`,
  };
}

export function formatMovimientoHistoryValue(item: HistorialErogacionItem, value: unknown, movement: Erogacion) {
  return readableValue(item, value, movement);
}
