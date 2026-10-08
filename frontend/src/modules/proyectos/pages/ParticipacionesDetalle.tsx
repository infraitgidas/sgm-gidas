import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import { useAuth } from "@/context/AuthContext";
import { navigateBackFromMemoriaContext, stripSuccessMessageState } from "@/lib/memoriaNavigation";
import {
  getHistorialParticipacionById,
  getParticipacionById,
} from "@/modules/proyectos/services/participacionesServices";
import {
  formatParticipacionHistoryEntry,
  presentParticipacionHistoryItems,
} from "@/modules/proyectos/utils/participacionHistory";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { formatFechaHora } from "@/utils/dateTime";
import { toTitleCase } from "@/utils/format";

const FORMA_LABELS: Record<string, string> = {
  jurado: "Jurado",
  evaluador: "Evaluador",
  panelista: "Panelista",
  comite: "Miembro de comité científico",
};

const formatDate = (value?: string | null) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value ?? "");
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value || "-";
};

export default function ParticipacionesDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const participacionId = id ? Number(id) : undefined;
  const detail = useQuery({
    queryKey: ["participacion", participacionId],
    queryFn: () => getParticipacionById(participacionId!),
    enabled: Boolean(participacionId),
    refetchOnMount: "always",
  });
  const history = useQuery({
    queryKey: ["participacion-historial", participacionId],
    queryFn: () => getHistorialParticipacionById(participacionId!),
    enabled: Boolean(participacionId),
    refetchOnMount: "always",
  });
  const auditoria = useAuditoria(detail.data);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!location.state?.successMessage) return;
    setSuccessMessage(location.state.successMessage);
    setShowSuccess(true);
    navigate(location.pathname, { replace: true, state: stripSuccessMessageState(location.state) });
  }, [location.pathname, location.state, navigate]);

  if (detail.isLoading) return <LoadingSkeleton variant="detail" label="Cargando participación…" />;
  if (detail.isError || !detail.data) {
    return <div role="alert" className="space-y-3 text-slate-600"><p>Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p><Button size="sm" onClick={() => detail.refetch()}>Reintentar</Button></div>;
  }

  const data = detail.data;
  const isDeleted = Boolean(data.deleted_at);
  const historyItems = presentParticipacionHistoryItems(history.data ?? []);

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between gap-4"><div className="flex flex-col gap-2"><h2 className="text-2xl font-semibold leading-none md:text-3xl">{toTitleCase(data.nombre_evento) || "-"}</h2><span className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${isDeleted ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>{isDeleted ? "INACTIVO" : "ACTIVO"}</span></div>{canEditRecords() && !isDeleted && <Button size="sm" onClick={() => navigate(`/participaciones/${participacionId}/editar`)}>Editar</Button>}</div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm"><div className="space-y-2 text-sm text-slate-500 md:text-base"><p><span className="font-semibold text-slate-800">Nombre del evento:</span> {toTitleCase(data.nombre_evento) || "-"}</p><p><span className="font-semibold text-slate-800">Participante:</span> {data.participante.nombre_apellido || "-"}</p><p><span className="font-semibold text-slate-800">Categoría:</span> {data.participante.tipo}</p><p><span className="font-semibold text-slate-800">Forma de participación:</span> {FORMA_LABELS[data.forma_participacion] ?? data.forma_participacion ?? "-"}</p><p><span className="font-semibold text-slate-800">Fecha:</span> {formatDate(data.fecha)}</p></div></article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm"><div className="mb-4"><h3 className="text-lg font-semibold text-slate-800">Auditoría</h3><p className="mt-1 text-xs text-slate-500">{toTitleCase(data.nombre_evento) || "-"}</p></div><div className="space-y-2 text-sm text-slate-500 md:text-base"><p><span className="font-semibold text-slate-800">Creado por:</span> {data.created_by_nombre || auditoria.nombreCreador}</p><p><span className="font-semibold text-slate-800">Fecha de creación:</span> {formatFechaHora(data.created_at)}</p><p><span className="font-semibold text-slate-800">Eliminado por:</span> {data.deleted_by_nombre || auditoria.nombreEliminador}</p><p><span className="font-semibold text-slate-800">Fecha de eliminación:</span> {formatFechaHora(data.deleted_at)}</p></div></article>

        {history.isError ? <article className="rounded-2xl border border-rose-200 bg-rose-50 p-6" role="alert"><p className="text-sm text-rose-700">Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</p><Button className="mt-3" size="sm" variant="secondary" onClick={() => history.refetch()}>Reintentar</Button></article> : <HistorialCambiosCard subtitle={toTitleCase(data.nombre_evento) || "-"} items={historyItems} isLoading={history.isLoading} updatedAt={data.updated_at} updatedByName={data.updated_by_nombre} formatItemValue={(item, value) => { const presentation = formatParticipacionHistoryEntry({ ...item, valor_anterior: value, valor_nuevo: value }); return presentation.description.split(" → ")[0]; }} />}

        <div className="flex justify-start pt-4"><Button variant="secondary" size="sm" onClick={() => navigateBackFromMemoriaContext(navigate, location, "/participaciones")}>Volver</Button></div>
      </section>
      <SuccessToast open={showSuccess} message={successMessage} onClose={() => setShowSuccess(false)} />
    </>
  );
}
