import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import { formatFechaHora } from "@/utils/dateTime";
import SuccessToast from "@/components/SuccessToast";
import {
  getDistincionById,
  getHistorialDistincionById,
} from "@/modules/produccion/services/distincionesServices";
import { getProyectos } from "@/modules/proyectos/services/proyectosServices";
import {
  formatDistincionHistoryEntry,
  presentDistincionHistoryItems,
} from "@/modules/produccion/utils/distincionHistory";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { useAuth } from "@/context/AuthContext";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

export default function DistincionesDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();

  const puedeEditar = canEditRecords();
  const distincionId = id ? Number(id) : undefined;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["distincion", distincionId],
    queryFn: () => getDistincionById(distincionId as number),
    enabled: !!distincionId,
    refetchOnMount: "always",
  });

  const historial = useQuery({
    queryKey: ["distincion-historial", distincionId],
    queryFn: () => getHistorialDistincionById(distincionId as number),
    enabled: !!distincionId,
    refetchOnMount: "always",
  });

  const { data: proyectos = [] } = useQuery({
    queryKey: ["proyectos", "all"],
    queryFn: () => getProyectos("all"),
    staleTime: 5 * 60_000,
  });

  const auditoria = useAuditoria(data);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const projectNames = useMemo(
    () =>
      Object.fromEntries(
        proyectos
          .filter((proyecto) => proyecto.id)
          .map((proyecto) => [
            Number(proyecto.id),
            `${proyecto.codigoProyecto} - ${proyecto.nombreProyecto}`,
          ])
      ),
    [proyectos]
  );
  const historialVisible = useMemo(
    () => presentDistincionHistoryItems(historial.data ?? []),
    [historial.data]
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

  const formatFecha = (fecha?: string | Date | null) => {
    if (!fecha) return "-";

    if (fecha instanceof Date) {
      const d = String(fecha.getDate()).padStart(2, "0");
      const m = String(fecha.getMonth() + 1).padStart(2, "0");
      const y = fecha.getFullYear();
      return `${d}/${m}/${y}`;
    }

    const dateStr = String(fecha);

    if (dateStr.includes("T")) {
      const date = new Date(dateStr);
      if (!isNaN(date.getTime())) {
        const d = String(date.getDate()).padStart(2, "0");
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const y = date.getFullYear();
        return `${d}/${m}/${y}`;
      }
    }

    if (dateStr.includes("-")) {
      const [y, m, d] = dateStr.split("-");
      return `${d}/${m}/${y}`;
    }

    return dateStr;
  };

  if (isLoading) return <LoadingSkeleton variant="detail" label="Cargando distinción..." />;
  if (isError || !data) {
    return <p role="alert" className="text-slate-500">Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>;
  }

  const isDeleted = !!data.deleted_at || data.activo === false;

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              {data.descripcion || "-"}
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
            <Button
              size="sm"
              onClick={() => navigate(`/distinciones/${distincionId}/editar`)}
            >
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Fecha:</span>{" "}
              {formatFecha(data.fecha)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Descripción:</span>{" "}
              {data.descripcion || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Proyecto de investigación:
              </span>{" "}
              {data.proyecto
                ? `${data.proyecto.codigo} - ${data.proyecto.nombre}`
                : "-"}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
            <p className="mt-1 text-xs text-slate-500">
              {data.descripcion || "-"}
            </p>
          </div>

          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Creado por:</span>{" "}
              {auditoria.nombreCreador}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Fecha de creación:
              </span>{" "}
              {formatFechaHora(data.created_at)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Eliminado por:</span>{" "}
              {auditoria.nombreEliminador}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Fecha de eliminación:
              </span>{" "}
              {formatFechaHora(data.deleted_at)}
            </p>
          </div>
        </article>

        {historial.isError ? (
          <article role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-rose-800">Historial de cambios</h3>
            <p className="mt-2 text-sm text-rose-700">
              Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.
            </p>
            <Button
              className="mt-4"
              variant="secondary"
              size="sm"
              onClick={() => historial.refetch()}
            >
              Reintentar
            </Button>
          </article>
        ) : (
          <HistorialCambiosCard
            subtitle={data.descripcion || "-"}
            items={historialVisible}
            isLoading={historial.isLoading}
            updatedAt={data.updated_at}
            updatedByName={data.updated_by_nombre}
            formatItemPresentation={(item) =>
              formatDistincionHistoryEntry(item, projectNames)
            }
          />
        )}

        <div className="flex justify-start pt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigateBackFromMemoriaContext(navigate, location, "/distinciones")
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
