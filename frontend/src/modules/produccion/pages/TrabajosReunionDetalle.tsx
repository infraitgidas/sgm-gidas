import LoadingSkeleton from "@/components/LoadingSkeleton";
import { enlaceSeguro } from "@/modules/produccion/utils/trabajoEnlace";
import { autorEtiqueta } from "@/modules/produccion/services/trabajoAutoresServices";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, useMemo } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import {
  getHistorialTrabajoReunionById,
  getTrabajoReunionById,
  type TrabajoReunion,
} from "@/modules/produccion/services/trabajosReunionServices";
import { useAuth } from "@/context/AuthContext";
import { toTitleCase } from "@/utils/format";
import { useTiposReunion } from "@/modules/produccion/hooks/useTiposReunion";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";
import { formatTrabajoReunionAuthorHistoryEntry } from "@/modules/produccion/utils/trabajoReunionHistory";

export default function TrabajoReunionDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const { tipos = [] } = useTiposReunion();

  const puedeEditar = canEditRecords();
  const trabajoId = id ? Number(id) : undefined;

  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const { data, isLoading, isError } = useQuery<TrabajoReunion>({
    queryKey: ["trabajo-reunion", trabajoId],
    queryFn: () => getTrabajoReunionById(trabajoId as number),
    enabled: !!trabajoId,
    refetchOnMount: "always",
  });

  const { data: historialCambios = [], isLoading: isLoadingHistorial } = useQuery({
    queryKey: ["trabajo-reunion-historial", trabajoId],
    queryFn: () => getHistorialTrabajoReunionById(trabajoId as number),
    enabled: !!trabajoId,
    refetchOnMount: "always",
  });

  const historialVisible = useMemo(() => historialCambios.map(item => ({ ...item,
    campo: ["fecha_inicio", "fecha_presentacion"].includes(item.campo ?? "") ? "Fecha de presentación" : item.campo,
  })), [historialCambios]);

  const auditoria = useAuditoria(data);

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
    return <p className="text-slate-500">Trabajo en reunión científica no encontrado.</p>;
  }

  const enlace = enlaceSeguro(data.enlace);
  const isDeleted = !!data.deleted_at || data.activo === false;

  const formatHistorialValue = (
    item: { campo?: string },
    value: unknown,
    kind: "anterior" | "nuevo"
  ) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const asNumber =
      typeof value === "number"
        ? value
        : typeof value === "string" && value.trim() !== ""
          ? Number(value)
          : NaN;

    if (item.campo === "Fecha de presentación" && typeof value === "string") return formatFecha(value);

    if (item.campo === "tipo_reunion_id") {
      return tipos.find((tipo) => tipo.id === asNumber)?.nombre ?? String(value);
    }

    if (item.campo === "autores" && typeof value === "object" && value !== null) {
      const payload = value as {
        accion?: string;
        detalle?: { nombre_apellido?: string; tipo?: string };
      };
      if (kind === "anterior") {
        return "-";
      }
      return payload.detalle?.nombre_apellido
        ? `${payload.accion === "desvincular" ? "Desvinculado" : "Vinculado"}: ${payload.detalle.nombre_apellido}${payload.detalle.tipo ? ` (${payload.detalle.tipo})` : ""}` : "Autor";
    }

    if (typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch {
        return "-";
      }
    }

    return String(value);
  };

  const autores = data.autores?.length ? data.autores.map(autorEtiqueta).join(", ") : "-";

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              {data.titulo_trabajo || "-"}
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
            <Button size="sm" onClick={() => navigate(`/trabajos-reunion/${data.id}/editar`)}>
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-2 break-words text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Reunión:</span>{" "}
              {toTitleCase(data.nombre_reunion) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Tipo de reunión:</span>{" "}
              {toTitleCase(data.tipo_reunion?.nombre) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Procedencia:</span>{" "}
              {toTitleCase(data.procedencia) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de presentación:</span>{" "}
              {formatFecha(data.fecha_presentacion)}
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
            <p className="mt-1 text-xs text-slate-500">{data.titulo_trabajo || "-"}</p>
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
          subtitle={data.titulo_trabajo || "-"}
          items={historialVisible}
          isLoading={isLoadingHistorial}
          updatedAt={data.updated_at}
          updatedByName={data.updated_by_nombre}
          formatItemValue={(item, value, kind) =>
            formatHistorialValue(item, value, kind)
          }
          formatItemPresentation={formatTrabajoReunionAuthorHistoryEntry}
        />

        <div className="flex justify-start pt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigateBackFromMemoriaContext(navigate, location, "/trabajos-reunion")
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
