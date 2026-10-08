import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import {
  getHistorialRegistroPropiedadById,
  getRegistroPropiedadById,
  type RegistroPropiedad,
} from "@/modules/produccion/services/registrosPropiedadServices";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { useAuth } from "@/context/AuthContext";
import { toTitleCase } from "@/utils/format";
import { useTiposRegistroPropiedad } from "@/modules/produccion/hooks/useTipoRegistroPropiedad";
import { presentRegistroPropiedadHistoryItems } from "@/modules/produccion/utils/registroPropiedadHistory";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

export default function RegistrosPropiedadDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const { tipos = [] } = useTiposRegistroPropiedad();

  const puedeEditar = canEditRecords();
  const registroId = id ? Number(id) : undefined;

  const { data, isLoading, isError } = useQuery<RegistroPropiedad>({
    queryKey: ["registro-propiedad", registroId],
    queryFn: () => getRegistroPropiedadById(registroId as number),
    enabled: !!registroId,
    refetchOnMount: "always",
  });

  const { data: historialCambios = [], isLoading: isLoadingHistorial } = useQuery({
    queryKey: ["registro-propiedad-historial", registroId],
    queryFn: () => getHistorialRegistroPropiedadById(registroId as number),
    enabled: !!registroId,
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

  if (isLoading) return <LoadingSkeleton variant="detail" label="Cargando..." />;
  if (isError || !data) {
    return <p className="text-slate-500">No se encontró el registro.</p>;
  }

  const isDeleted = !!data.deleted_at;

  const formatHistorialValue = (item: { campo?: string }, value: unknown) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const asNumber =
      typeof value === "number"
        ? value
        : typeof value === "string" && value.trim() !== ""
          ? Number(value)
          : NaN;

    switch (item.campo) {
      case "tipo_registro_id":
        return (
          tipos.find((tipo) => tipo.id === asNumber)?.nombre ?? String(value)
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
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              {data.nombre_articulo || "-"}
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
              onClick={() => navigate(`/registros-propiedad/${data.id}/editar`)}
            >
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">
                Nombre del artículo:
              </span>{" "}
              {data.nombre_articulo || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Organismo registrante:
              </span>{" "}
              {toTitleCase(data.organismo_registrante) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Fecha de registro:
              </span>{" "}
              {formatFecha(data.fecha_registro)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Tipo de registro:
              </span>{" "}
              {toTitleCase(data.tipo_registro) || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Grupo UTN:</span>{" "}
              {toTitleCase(data.grupo) || "-"}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
            <p className="mt-1 text-xs text-slate-500">
              {data.nombre_articulo || "-"}
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
              <span className="font-semibold text-slate-800">
                Eliminado por:
              </span>{" "}
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
          subtitle={data.nombre_articulo || "-"}
          items={presentRegistroPropiedadHistoryItems(historialCambios)}
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
                "/registros-propiedad"
              )
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
