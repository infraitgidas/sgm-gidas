import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import {
  getTransferenciaById,
  getHistorialTransferenciaById,
  type Transferencia,
} from "@/modules/transferencia/services/transferenciasServices";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { useAuth } from "@/context/AuthContext";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";
import { presentTransferenciaHistory, transferenciaHistoryEvent } from "@/modules/transferencia/utils/transferenciaHistory";
import { useAdoptanteHistorial } from "@/modules/transferencia/hooks/useAdoptantes";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

const formatMonto = (monto?: number | null) =>
  typeof monto === "number"
    ? monto.toLocaleString("es-AR", {
        style: "currency",
        currency: "ARS",
      })
    : "-";

export default function TransferenciasDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();

  const puedeEditar = canEditRecords();

  const { data, isLoading, isError, refetch: refetchTransferencia } = useQuery<Transferencia | null>({
    queryKey: ["transferencias", id],
    queryFn: () => getTransferenciaById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const {
    data: historialCambios = [],
    isLoading: isLoadingHistorial,
    isError: isHistorialError,
    refetch: refetchHistorial,
  } = useQuery({
    queryKey: ["transferencia-historial", id],
    queryFn: () => getHistorialTransferenciaById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [selectedAdoptanteId, setSelectedAdoptanteId] = useState<number | null>(null);
  const auditoria = useAuditoria(data);
  const adoptanteId = data?.adoptantes.some((item) => item.id === selectedAdoptanteId)
    ? selectedAdoptanteId ?? undefined
    : data?.adoptantes[0]?.id;
  const adoptanteHistorial = useAdoptanteHistorial(adoptanteId);

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

  if (isLoading) {
    return <LoadingSkeleton variant="detail" label="Cargando..." />;
  }

  if (isError) {
    return (
      <div role="alert" className="space-y-3 text-slate-600"><p>Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p><Button type="button" onClick={() => void refetchTransferencia()}>Reintentar</Button></div>
    );
  }

  if (!data) {
    return <p className="text-slate-500">No se encontró la transferencia.</p>;
  }

  const isDeleted = data.activo === false || !!data.deletedAt;
  const titulo = data.denominacion || data.descripcionActividad || "-";

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              {titulo}
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
            <Button size="sm" onClick={() => navigate(`/transferencias/${data.id}/editar`)}>
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Número de transferencia:</span>{" "}
              {data.numeroTransferencia || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Denominación:</span>{" "}
              {data.denominacion || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Demandante:</span>{" "}
              {data.demandante || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Descripción de la actividad:</span>{" "}
              {data.descripcionActividad || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Monto:</span>{" "}
              {formatMonto(data.monto)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de inicio:</span>{" "}
              {formatFecha(data.fechaInicio)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Fecha de fin:</span>{" "}
              {formatFecha(data.fechaFin)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Tipo de contrato:</span>{" "}
              {data.tipoContrato || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Grupo UTN:</span>{" "}
              {data.grupo || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Adoptantes:</span>{" "}
              {data.adoptantes.length > 0
                ? data.adoptantes.map((adoptante) => adoptante.nombre).join(", ")
                : "-"}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
            <p className="mt-1 text-xs text-slate-500">{titulo}</p>
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
              {formatFechaHora(data.deletedAt)}
            </p>
          </div>
        </article>

        <HistorialCambiosCard
          subtitle={titulo}
          items={presentTransferenciaHistory(historialCambios)}
          isLoading={isLoadingHistorial}
          updatedAt={data.updated_at}
          updatedByName={data.updated_by_nombre}
          formatItemPresentation={(item) => transferenciaHistoryEvent(item)}
          formatItemValue={(item, value) => {
            if (value === null || value === undefined || value === "") return "-";

            if (item.campo === "monto") {
              return formatMonto(Number(value));
            }

            if (item.campo === "fecha_inicio" || item.campo === "fecha_fin") {
              return formatFecha(String(value));
            }

            if (item.campo === "tipo_contrato_id") {
              const idValue = Number(value);
              return idValue === data.tipoContratoId ? data.tipoContrato || "Dato actualizado" : "Dato actualizado";
            }

            if (item.campo === "grupo_utn_id") {
              const idValue = Number(value);
              return idValue === data.grupoUtnId ? data.grupo || "Dato actualizado" : "Dato actualizado";
            }

            if (item.campo === "adoptantes") {
              if (
                typeof value === "object" &&
                value !== null &&
                "detalle" in value &&
                typeof (value as { detalle?: unknown }).detalle === "object" &&
                (value as { detalle?: unknown }).detalle !== null &&
                "nombre" in ((value as { detalle: { nombre?: string } }).detalle)
              ) {
                return String(
                  (value as { detalle: { nombre?: string } }).detalle.nombre || "-"
                );
              }

              if (Array.isArray(value)) {
                const nombres = value
                  .map((entry) => {
                    if (typeof entry === "string") {
                      return entry
                        .replace(/^vincular:\s*/i, "")
                        .replace(/^desvincular:\s*/i, "");
                    }

                    if (typeof entry === "object" && entry !== null && "nombre" in entry) {
                      return String((entry as { nombre?: string }).nombre || "");
                    }

                    return "";
                  })
                  .filter(Boolean);

                return nombres.length > 0 ? nombres.join(", ") : "-";
              }

              if (typeof value === "string") {
                return value.replace(/^vincular:\s*/i, "").replace(/^desvincular:\s*/i, "");
              }

              if (typeof value === "object" && value !== null && "nombre" in value) {
                return String((value as { nombre?: string }).nombre || "-");
              }
            }

            return String(value);
          }}
        />

        {isHistorialError && (
          <p className="text-sm text-red-600" role="alert">
            Lo sentimos, no pudimos recuperar el historial. <button type="button" className="underline" onClick={() => refetchHistorial()}>Reintentar</button>
          </p>
        )}

        <section aria-labelledby="adoptantes-historial-titulo" className="space-y-3">
          <h3 id="adoptantes-historial-titulo" className="text-lg font-semibold text-slate-700">Historial de cambios de adoptantes</h3>
          {data.adoptantes.length > 0 ? (
            <>
              <div className="max-w-md">
                <label htmlFor="adoptante-historial" className="mb-1 block text-sm font-medium text-slate-700">Adoptante</label>
                <select
                  id="adoptante-historial"
                  value={adoptanteId}
                  onChange={(event) => setSelectedAdoptanteId(Number(event.target.value))}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                >
                  {data.adoptantes.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
                </select>
              </div>
              <HistorialCambiosCard
                key={adoptanteId}
                title="Cambios de campos del adoptante"
                subtitle={data.adoptantes.find((item) => item.id === adoptanteId)?.nombre}
                items={adoptanteHistorial.data ?? []}
                isLoading={adoptanteHistorial.isLoading}
                pageSize={3}
              />
              {adoptanteHistorial.isError && (
                <p role="alert" className="text-sm text-red-600">
                  Lo sentimos, no pudimos recuperar el historial del adoptante. <button type="button" className="underline" onClick={() => void adoptanteHistorial.refetch()}>Reintentar</button>
                </p>
              )}
            </>
          ) : <p className="text-sm text-slate-500">No hay adoptantes vinculados a esta transferencia.</p>}
        </section>

        <div className="flex justify-start pt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigateBackFromMemoriaContext(navigate, location, "/transferencias")
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
