import LoadingSkeleton from "@/components/LoadingSkeleton";
import { enlaceSeguro } from "@/modules/produccion/utils/trabajoEnlace";
import { autorEtiqueta } from "@/modules/produccion/services/trabajoAutoresServices";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";
import { toTitleCase } from "@/utils/format";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import {
  getHistorialTrabajoRevistaById,
  getTrabajoRevistaById,
  type TrabajoRevista,
} from "@/modules/produccion/services/trabajosRevistasServices";
import { useAuth } from "@/context/AuthContext";
import { useTiposRevista } from "@/modules/produccion/hooks/useTiposRevista";
import {
  formatTrabajoRevistaHistoryEntry,
  presentTrabajoRevistaHistoryItems,
} from "@/modules/produccion/utils/trabajoRevistaHistory";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

export default function TrabajoRevistaDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const { tipos = [] } = useTiposRevista();

  const puedeEditar = canEditRecords();
  const trabajoId = id ? Number(id) : undefined;

  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const { data, isLoading, isError } = useQuery<TrabajoRevista>({
    queryKey: ["trabajo-revista", trabajoId],
    queryFn: () => getTrabajoRevistaById(trabajoId as number),
    enabled: !!trabajoId,
    refetchOnMount: "always",
  });

  const { data: historialCambios = [], isLoading: isLoadingHistorial } = useQuery({
    queryKey: ["trabajo-revista-historial", trabajoId],
    queryFn: () => getHistorialTrabajoRevistaById(trabajoId as number),
    enabled: !!trabajoId,
    refetchOnMount: "always",
  });

  const auditoria = useAuditoria(data);
  const tipoNames = useMemo(
    () => Object.fromEntries(tipos.map((tipo) => [tipo.id, tipo.nombre])),
    [tipos]
  );
  const historialVisible = useMemo(
    () => presentTrabajoRevistaHistoryItems(historialCambios),
    [historialCambios]
  );

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

  if (isLoading) return <LoadingSkeleton variant="detail" label="Cargando..." />;
  if (isError || !data) {
    return <p className="text-slate-500">Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>;
  }

  const enlace = enlaceSeguro(data.enlace);
  const isDeleted = !!data.deleted_at || data.activo === false;

  const autores = data.autores?.length ? data.autores.map(autorEtiqueta).join(", ") : "-";

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              {toTitleCase(data.titulo_trabajo) || "-"}
            </h2>

            <span
              className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
                isDeleted
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-emerald-200 bg-emerald-50 text-emerald-700"
              }`}
            >
              {isDeleted ? "INACTIVO" : "ACTIVO"}
            </span>
          </div>

          {puedeEditar && !isDeleted && (
            <Button size="sm" onClick={() => navigate(`/trabajos-revistas/${data.id}/editar`)}>
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-3 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Revista:</span>{" "}
              {toTitleCase(data.nombre_revista) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Editorial:</span>{" "}
              {toTitleCase(data.editorial) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">ISSN:</span>{" "}
              {data.issn || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">País:</span>{" "}
              {toTitleCase(data.pais) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Tipo de revista:</span>{" "}
              {toTitleCase(data.tipo_revista?.nombre) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de publicación:</span>{" "}
              {formatFecha(data.fecha_publicacion)}
            </p>

            {enlace && <p className="break-words">
              <span className="font-semibold text-slate-800">Enlace al trabajo o DOI:</span>{" "}
              <a href={enlace} target="_blank" rel="noopener noreferrer"
                className="text-blue-700 underline focus-visible:outline focus-visible:outline-2">
                {enlace}<span className="sr-only"> (abre en una pestaña nueva)</span>
              </a>
            </p>}

            <p>
              <span className="font-semibold text-slate-800">Autores:</span>{" "}
              {autores}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
            <p className="mt-1 text-xs text-slate-500">
              {toTitleCase(data.titulo_trabajo) || "-"}
            </p>
          </div>

          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Creado por:</span>{" "}
              {auditoria.nombreCreador}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de creación:</span>{" "}
              {formatFechaHora(data.created_at)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Eliminado por:</span>{" "}
              {auditoria.nombreEliminador}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de eliminación:</span>{" "}
              {formatFechaHora(data.deleted_at)}
            </p>
          </div>
        </article>

        <HistorialCambiosCard
          subtitle={toTitleCase(data.titulo_trabajo) || "-"}
          items={historialVisible}
          isLoading={isLoadingHistorial}
          updatedAt={data.updated_at}
          updatedByName={data.updated_by_nombre}
          formatItemPresentation={(item) =>
            formatTrabajoRevistaHistoryEntry(item, tipoNames)
          }
        />

        <div className="flex justify-start pt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigateBackFromMemoriaContext(navigate, location, "/trabajos-revistas")
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
