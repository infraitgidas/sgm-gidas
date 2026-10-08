import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import { formatFechaHora } from "@/utils/dateTime";
import SuccessToast from "@/components/SuccessToast";
import {
  getActividadDocenciaById,
  getHistorialActividadDocenciaById,
} from "@/modules/produccion/services/actividadDocenciaServices";
import { useGradosAcademicos } from "@/modules/produccion/hooks/useGradoAcademico";
import { useRolesActividadDocencia } from "@/modules/produccion/hooks/useActividadDocenciaRol";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { toTitleCase } from "@/utils/format";
import { useAuth } from "@/context/AuthContext";
import {
  getActividadDocenciaHistoryCatalogName,
  presentActividadDocenciaHistoryItems,
} from "@/modules/produccion/utils/actividadDocenciaHistory";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

export default function ActividadDocenciaDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const { data: gradosAcademicos = [] } = useGradosAcademicos();
  const { data: rolesActividad = [] } = useRolesActividadDocencia();
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const puedeEditar = canEditRecords();

  const { data, isLoading } = useQuery({
    queryKey: ["actividad-docencia", id],
    queryFn: () => getActividadDocenciaById(Number(id)),
    enabled: !!id,
  });

  const { data: historialCambios = [], isLoading: isLoadingHistorial } = useQuery({
    queryKey: ["actividad-docencia-historial", id],
    queryFn: () => getHistorialActividadDocenciaById(Number(id)),
    enabled: !!id,
  });

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
  if (!data)
    return <p className="text-slate-500">No se encontró la actividad.</p>;

  const isDeleted = !!data.deleted_at;

  const formatFecha = (fecha?: string | null) => {
    if (!fecha) return "-";
    const date = new Date(`${fecha}T00:00:00`);
    const dia = String(date.getDate()).padStart(2, "0");
    const mes = String(date.getMonth() + 1).padStart(2, "0");
    const anio = date.getFullYear();
    return `${dia}/${mes}/${anio}`;
  };

  const investigadorNombre =
    typeof data.investigador === "string"
      ? data.investigador
      : data.investigador?.nombre_apellido;

  const gradoActualNombre =
    data.grado_academico_actual?.nombre ?? data.grado_academico;

  const rolActividadNombre =
    rolesActividad.find((rol) => rol.id === data.rol_actividad_id)?.nombre ??
    data.rol_actividad;

  const formatHistorialValue = (
    item: { campo?: string; tipo?: string },
    value: unknown
  ) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const catalogName = getActividadDocenciaHistoryCatalogName(value);
    if (catalogName) return catalogName;

    const asNumber =
      typeof value === "number"
        ? value
        : typeof value === "string" && value.trim() !== ""
          ? Number(value)
          : NaN;

    switch (item.campo) {
      case "grado_academico_id":
        return (
          gradosAcademicos.find((grado) => grado.id === asNumber)?.nombre ??
          String(value)
        );
      case "rol_actividad_id":
        return (
          rolesActividad.find((rol) => rol.id === asNumber)?.nombre ??
          String(value)
        );
      default:
        if (typeof value === "object") {
          try {
            return JSON.stringify(value);
          } catch {
            return "-";
          }
        }
        return String(value);
    }
  };

  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-2">
          <h2 className="text-2xl md:text-3xl font-semibold leading-none">
            {toTitleCase(data.curso) || "-"}
          </h2>

          <span
            className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
              isDeleted
                ? "border-red-200 bg-red-50 text-red-700"
                : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            {isDeleted ? "ELIMINADA" : "ACTIVA"}
          </span>
        </div>

        {puedeEditar && !isDeleted && (
          <Button
            size="sm"
            onClick={() => navigate(`/docenciaInvestigador/${id}/editar`)}
          >
            Editar
          </Button>
        )}
      </div>

      <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="space-y-2 text-sm text-slate-500 md:text-base">
          <p>
            <span className="font-semibold text-slate-800">Investigador:</span>{" "}
            {toTitleCase(investigadorNombre) || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Fecha de inicio:</span>{" "}
            {formatFecha(data.fecha_inicio)}
          </p>

          <p>
            <span className="font-semibold text-slate-800">
              Fecha de finalizacion:
            </span>{" "}
            {formatFecha(data.fecha_fin)}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Grado academico:</span>{" "}
            {toTitleCase(gradoActualNombre) || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Institución:</span>{" "}
            {toTitleCase(data.institucion) || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">
              Rol en la actividad:
            </span>{" "}
            {toTitleCase(rolActividadNombre) || "-"}
          </p>
        </div>
      </article>

      <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>

          <p className="mt-1 text-xs text-slate-500">
            {toTitleCase(data.curso) || "-"} - {toTitleCase(investigadorNombre) || "-"}
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

      <HistorialCambiosCard
        subtitle={`${toTitleCase(data.curso) || "-"} - ${
          toTitleCase(investigadorNombre) || "-"
        }`}
        items={presentActividadDocenciaHistoryItems(historialCambios)}
        isLoading={isLoadingHistorial}
        updatedAt={data.updated_at}
        updatedByName={data.updated_by_nombre}
        formatItemValue={(item, value) => formatHistorialValue(item, value)}
      />

      <div className="flex justify-start pt-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() =>
            navigateBackFromMemoriaContext(
              navigate,
              location,
              "/docenciaInvestigador"
            )
          }
        >
          Volver
        </Button>
      </div>

      <SuccessToast
        open={showSuccess}
        message={successMessage}
        onClose={() => setShowSuccess(false)}
      />
    </section>
  );
}
