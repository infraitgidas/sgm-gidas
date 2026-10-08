import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import { useAuth } from "@/context/AuthContext";
import { navigateBackFromMemoriaContext, stripSuccessMessageState } from "@/lib/memoriaNavigation";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import {
  getErogacionById, getHistorialErogacionById,
} from "@/modules/recursos/services/erogacionesServices";
import { formatMovimientoHistoryValue, formatMovimientoMoney, presentMovimientoHistoryItems } from "@/modules/recursos/utils/movimientoHistory";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";

export default function ErogacionesDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const [successMessage, setSuccessMessage] = useState("");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["erogaciones", id],
    queryFn: () => getErogacionById(Number(id)),
    enabled: Boolean(id),
    refetchOnMount: "always",
  });
  const { data: historial = [], isLoading: loadingHistorial, isError: historialError, refetch: refetchHistorial } = useQuery({
    queryKey: ["erogacion-historial", id],
    queryFn: () => getHistorialErogacionById(Number(id)),
    enabled: Boolean(id),
    refetchOnMount: "always",
  });
  const auditoria = useAuditoria(data);

  useEffect(() => {
    if (!location.state?.successMessage) return;
    setSuccessMessage(location.state.successMessage);
    navigate(location.pathname, {
      replace: true,
      state: stripSuccessMessageState(location.state),
    });
  }, [location.state, location.pathname, navigate]);

  if (isLoading) return <LoadingSkeleton variant="detail" label="Cargando movimiento..." />;
  if (isError || !data) return <div role="alert" className="flex items-center gap-3 text-slate-600">Lo sentimos, no pudimos recuperar el movimiento. Intente nuevamente.<Button size="sm" variant="secondary" onClick={() => refetch()}>Reintentar</Button></div>;

  const titulo = `Movimiento N.º ${String(data.numero_movimiento).padStart(6, "0")}`;
  const isDeleted = Boolean(data.deleted_at);
  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold md:text-3xl">{titulo}</h2>
            <span className={`mt-2 inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${isDeleted
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
              {isDeleted ? "INACTIVO" : "ACTIVO"}
            </span>
          </div>
          {canEditRecords() && !isDeleted && <Button size="sm" onClick={() => navigate(`/movimientos/${data.id}/editar`)}>Editar</Button>}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <dl className="grid gap-4 text-sm md:grid-cols-2 md:text-base">
            <div><dt className="font-semibold text-slate-800">Tipo de movimiento</dt><dd className="text-slate-600">{data.tipo_movimiento === "INGRESO" ? "Ingreso" : "Egreso"}</dd></div>
            <div><dt className="font-semibold text-slate-800">Fecha</dt><dd className="text-slate-600">{formatFecha(data.fecha)}</dd></div>
            <div><dt className="font-semibold text-slate-800">Monto</dt><dd className="text-slate-600">{formatMovimientoMoney(data.monto, data.moneda)}</dd></div>
            <div><dt className="font-semibold text-slate-800">Moneda</dt><dd className="text-slate-600">{data.moneda}</dd></div>
            {data.moneda === "USD" && <>
              <div><dt className="font-semibold text-slate-800">Cotización oficial diaria utilizada</dt><dd className="text-slate-600">ARS {data.tipo_cambio_aplicado} / USD</dd></div>
              <div><dt className="font-semibold text-slate-800">Fecha de cotización</dt><dd className="text-slate-600">{data.tipo_cambio ? formatFecha(data.tipo_cambio.fecha_cotizacion) : "—"}</dd></div>
              <div><dt className="font-semibold text-slate-800">Equivalente en ARS</dt><dd className="text-slate-600">{data.monto_equivalente_ars ? formatMovimientoMoney(data.monto_equivalente_ars, "ARS") : "—"}</dd></div>
              <div><dt className="font-semibold text-slate-800">Fuente</dt><dd className="text-slate-600">Banco Central de la República Argentina · {data.tipo_cambio?.serie_bcra === 7927
                ? "Tipo de Cambio Minorista · Com. B 9791 · Promedio vendedor"
                : `Serie ${data.tipo_cambio?.serie_bcra ?? "—"}`}</dd></div>
            </>}
            <div><dt className="font-semibold text-slate-800">Fuente de financiamiento</dt><dd className="text-slate-600">{data.fuente?.nombre ?? "—"}</dd></div>
            {data.tipo_movimiento === "EGRESO" && <>
              <div><dt className="font-semibold text-slate-800">Categoría de erogación</dt><dd className="text-slate-600">{data.categoria_erogacion?.nombre ?? "—"}</dd></div>
              <div><dt className="font-semibold text-slate-800">Equipamiento relacionado</dt><dd className="text-slate-600">{data.equipamiento?.denominacion ?? "—"}</dd></div>
            </>}
          </dl>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
          <p className="mt-1 text-xs text-slate-500">{titulo}</p>
          <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2 md:text-base">
            <div><dt className="font-semibold text-slate-800">Creado por</dt><dd className="text-slate-500">{data.created_by_nombre || auditoria.nombreCreador}</dd></div>
            <div><dt className="font-semibold text-slate-800">Fecha de creación</dt><dd className="text-slate-500">{formatFechaHora(data.created_at)}</dd></div>
            <div><dt className="font-semibold text-slate-800">Eliminado por</dt><dd className="text-slate-500">{data.deleted_by_nombre || auditoria.nombreEliminador}</dd></div>
            <div><dt className="font-semibold text-slate-800">Fecha de eliminación</dt><dd className="text-slate-500">{formatFechaHora(data.deleted_at)}</dd></div>
          </dl>
        </article>

        {historialError && <div role="alert" className="flex items-center gap-3 text-sm text-rose-700">Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.<Button size="sm" variant="secondary" onClick={() => refetchHistorial()}>Reintentar</Button></div>}
        <HistorialCambiosCard subtitle={titulo} items={presentMovimientoHistoryItems(historial)} isLoading={loadingHistorial}
          updatedAt={data.updated_at} updatedByName={data.updated_by_nombre}
          formatItemValue={(item, value) => formatMovimientoHistoryValue(item, value, data)}
        />
        <div className="pt-4"><Button size="sm" variant="secondary" onClick={() => navigateBackFromMemoriaContext(navigate, location, "/movimientos")}>Volver</Button></div>
      </section>
      <SuccessToast open={Boolean(successMessage)} message={successMessage} onClose={() => setSuccessMessage("")} />
    </>
  );
}
