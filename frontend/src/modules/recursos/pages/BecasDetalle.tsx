import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import SuccessToast from "@/components/SuccessToast";
import { useAuth } from "@/context/AuthContext";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { getBecaById, getBecaHistorial } from "@/modules/recursos/services/becasService";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";

export default function BecasDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const [success, setSuccess] = useState("");
  const beca = useQuery({ queryKey: ["beca", id], queryFn: () => getBecaById(Number(id)), enabled: Boolean(id) });
  const history = useQuery({ queryKey: ["beca-historial", id], queryFn: () => getBecaHistorial(Number(id)), enabled: Boolean(id) });
  const auditoria = useAuditoria(beca.data);

  useEffect(() => {
    const message = (location.state as { successMessage?: string } | null)?.successMessage;
    if (!message) return;
    setSuccess(message);
    navigate(location.pathname, { replace: true });
  }, [location.pathname, location.state, navigate]);

  if (beca.isLoading) return <LoadingSkeleton variant="detail" label="Cargando beca..." />;
  if (beca.isError || !beca.data) return <p role="alert">Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>;
  const item = beca.data;
  return <>
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-2xl font-semibold md:text-3xl">{item.nombre_beca}</h2><span className="text-sm text-slate-600">{item.deleted_at ? "Inactiva" : "Activa"}</span></div>
        {!item.deleted_at && canEditRecords() && <Button size="sm" onClick={() => navigate(`/becas/${item.id}/editar`)}>Editar</Button>}
      </div>
      <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-slate-800">Datos de la beca</h3>
        <dl className="grid gap-4 text-sm md:grid-cols-2">
          <div><dt className="font-semibold text-slate-800">Descripción</dt><dd className="mt-1 text-slate-600">{item.descripcion || "-"}</dd></div>
          <div><dt className="font-semibold text-slate-800">Fuente de financiamiento</dt><dd className="mt-1 text-slate-600">{item.fuente_financiamiento?.nombre ?? "-"}</dd></div>
          <div><dt className="font-semibold text-slate-800">Fecha de alta en el grupo</dt><dd className="mt-1 text-slate-600">{formatFecha(item.fecha_alta_grupo)}</dd></div>
        </dl>
      </article>
      <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-lg font-semibold text-slate-800">Becarios vinculados</h3>
          <span className="text-sm text-slate-500">{item.becarios?.length ?? 0} {item.becarios?.length === 1 ? "becario" : "becarios"}</span>
        </div>
        {!item.becarios?.length ? <p className="text-sm text-slate-600">No hay becarios vinculados.</p> :
          <ul className="grid gap-3 md:grid-cols-2">{item.becarios.map((becario) => <li key={becario.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <h4 className="text-base font-semibold text-slate-900">{becario.nombre_apellido}</h4>
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2">
              <div><dt className="text-xs font-medium text-slate-500">Inicio</dt><dd className="mt-0.5 text-slate-700">{formatFecha(becario.fecha_inicio)}</dd></div>
              <div><dt className="text-xs font-medium text-slate-500">Fin</dt><dd className="mt-0.5 text-slate-700">{becario.fecha_fin ? formatFecha(becario.fecha_fin) : "Sin fecha de fin"}</dd></div>
              {becario.monto_percibido != null && <div className="col-span-2"><dt className="text-xs font-medium text-slate-500">Monto percibido</dt><dd className="mt-0.5 text-slate-700">{new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(becario.monto_percibido)}</dd></div>}
            </dl>
          </li>)}</ul>}
      </article>
      <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-slate-800">Auditoría</h3>
        <dl className="grid gap-4 text-sm md:grid-cols-2">
          <div><dt className="font-semibold text-slate-800">Creado por</dt><dd>{item.created_by_nombre || auditoria.nombreCreador}</dd></div>
          <div><dt className="font-semibold text-slate-800">Fecha de creación</dt><dd>{formatFechaHora(item.created_at)}</dd></div>
          <div><dt className="font-semibold text-slate-800">Eliminado por</dt><dd>{item.deleted_by_nombre || auditoria.nombreEliminador}</dd></div>
          <div><dt className="font-semibold text-slate-800">Fecha de eliminación</dt><dd>{formatFechaHora(item.deleted_at)}</dd></div>
        </dl>
      </article>
      <HistorialCambiosCard items={history.data} isLoading={history.isLoading} subtitle={item.nombre_beca} pageSize={3}
        updatedAt={item.updated_at} updatedByName={item.updated_by_nombre}
        formatItemPresentation={(entry) => {
          if (entry.campo !== "becarios" || !entry.valor_nuevo || typeof entry.valor_nuevo !== "object") return null;
          const event = entry.valor_nuevo as { accion?: string; detalle?: { becario_id?: number } };
          const name = item.becarios?.find((becario) => becario.id === event.detalle?.becario_id)?.nombre_apellido;
          const action = event.accion === "vincular" ? "Vinculación" : event.accion === "desvincular" ? "Desvinculación" : "Actualización";
          return { title: `${action} de becario`, description: name ? `${name} · ${item.nombre_beca}` : `Se registró un cambio en los becarios de ${item.nombre_beca}.` };
        }}
        formatItemValue={(entry, value) => {
          if (value === null || value === undefined || value === "") return "-";
          if (entry.campo === "fecha_alta_grupo") return formatFecha(String(value));
          if (entry.campo === "fuente_financiamiento_id") return Number(value) === item.fuente_financiamiento_id ? item.fuente_financiamiento?.nombre ?? "Fuente" : "Otra fuente";
          return typeof value === "object" ? "Cambio en vinculación" : String(value);
        }} />
      {history.isError && <div role="alert" className="text-sm text-rose-700">No pudimos cargar el historial. <button type="button" className="underline" onClick={() => void history.refetch()}>Reintentar</button></div>}
      <div><Button variant="secondary" size="sm" onClick={() => navigate("/becas")}>Volver</Button></div>
    </section>
    <SuccessToast open={Boolean(success)} message={success} onClose={() => setSuccess("")} />
  </>;
}
