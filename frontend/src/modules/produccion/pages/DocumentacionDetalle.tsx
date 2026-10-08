import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import {
  getDocumentacionById,
  getHistorialDocumentacionById,
  type Documentacion,
} from "@/modules/produccion/services/documentacionServices";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { useAuth } from "@/context/AuthContext";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";
import { formatDocumentacionAuthorHistoryEntry, formatDocumentacionHistoryValue, presentDocumentacionHistoryItems } from "@/modules/produccion/utils/documentacionHistory";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

const formatTitulo = (titulo?: string | null) =>
  titulo
    ? titulo
        .toLowerCase()
        .split(" ")
        .map((word) => (word ? word.charAt(0).toUpperCase() + word.slice(1) : ""))
        .join(" ")
    : "-";

export default function DocumentacionDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();

  const puedeEditar = canEditRecords();

  const { data, isLoading, isError } = useQuery<Documentacion>({
    queryKey: ["documentacion", id],
    queryFn: () => getDocumentacionById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const { data: historialCambios = [], isLoading: isLoadingHistorial, isError: isHistoryError, refetch: retryHistory } = useQuery({
    queryKey: ["documentacion-historial", id],
    queryFn: () => getHistorialDocumentacionById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const auditoria = useAuditoria(data);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (location.state?.successMessage) {
      setSuccessMessage(location.state.successMessage);
      setShowSuccess(true);
      navigate(location.pathname, {
        replace: true,
        state: stripSuccessMessageState(location.state),
      });
    }
  }, [location.state, navigate, location.pathname]);

  if (isLoading) return <LoadingSkeleton variant="detail" label="Cargando documentación..." />;
  if (isError || !data) {
    return <p role="alert" className="text-slate-500">Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>;
  }

  const autores = data.autores?.length
    ? data.autores.map((autor) => autor.nombre_apellido).join(", ")
    : "-";

  const tituloFormateado = formatTitulo(data.titulo);
  const isDeleted = !!data.deleted_at;

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              {tituloFormateado}
            </h2>

            <span
              className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
                isDeleted
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-emerald-200 bg-emerald-50 text-emerald-700"
              }`}
            >
              {isDeleted ? "INACTIVA" : "ACTIVA"}
            </span>
          </div>

          {puedeEditar && !isDeleted && (
            <Button size="sm" onClick={() => navigate(`/documentacion/${id}/editar`)}>
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Autores:</span> {autores}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Editorial:</span>{" "}
              {data.editorial || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Año:</span> {data.anio || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha:</span>{" "}
              {formatFecha(data.fecha)}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
            <p className="mt-1 text-xs text-slate-500">{tituloFormateado}</p>
          </div>

          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Creado por:</span>{" "}
              {data.created_by_nombre || auditoria.nombreCreador}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de creación:</span>{" "}
              {formatFechaHora(data.created_at)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Eliminado por:</span>{" "}
              {data.deleted_by_nombre || auditoria.nombreEliminador}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de eliminación:</span>{" "}
              {formatFechaHora(data.deleted_at)}
            </p>
          </div>
        </article>

        {isHistoryError && <div role="alert" className="text-sm text-rose-700">Lo sentimos, no pudimos recuperar el historial. <Button type="button" variant="secondary" size="sm" onClick={() => retryHistory()}>Reintentar</Button></div>}
        <HistorialCambiosCard
          subtitle={tituloFormateado}
          items={presentDocumentacionHistoryItems(historialCambios)}
          isLoading={isLoadingHistorial}
          updatedAt={data.updated_at}
          updatedByName={data.updated_by_nombre}
          formatItemValue={formatDocumentacionHistoryValue}
          formatItemPresentation={formatDocumentacionAuthorHistoryEntry}
        />

        <div className="flex justify-start pt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigateBackFromMemoriaContext(navigate, location, "/documentacion")
            }
          >
            Volver
          </Button>
        </div>
      </section>

      <SuccessToast
        open={showSuccess}
        message={successMessage}
        onClose={() => setShowSuccess(false)}
      />
    </>
  );
}
