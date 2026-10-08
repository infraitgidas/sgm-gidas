import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import { formatFechaHora, getLocalTodayIso } from "@/utils/dateTime";
import SuccessToast from "@/components/SuccessToast";
import {
  getProyectoById,
  getHistorialProyectoById,
  reabrirProyecto,
  prorrogarProyecto,
  type Proyecto,
} from "@/modules/proyectos/services/proyectosServices";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { useAuth } from "@/context/AuthContext";
import { useTiposProyecto } from "@/modules/proyectos/hooks/useTiposProyecto";
import { useFuentesFinanciamiento } from "@/modules/catalogos/hooks/useFuenteFinanciamiento";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";
import { formatProyectoRelationHistoryEntry } from "@/modules/proyectos/utils/proyectoHistory";
import { getErrorMessage, mapFieldErrors } from "@/lib/httpError";

export default function ProyectoDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const { canEditRecords, isGestor } = useAuth();
  const { data: tiposProyecto = [] } = useTiposProyecto();
  const { fuentes = [] } = useFuentesFinanciamiento();

  const puedeEditar = canEditRecords();
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [motivoProrroga, setMotivoProrroga] = useState("");
  const [prorrogaError, setProrrogaError] = useState("");
  const prorrogaSubmitting = useRef(false);

  const { data, isLoading } = useQuery<Proyecto | null>({
    queryKey: ["proyecto", id],
    queryFn: () => (id ? getProyectoById(Number(id)) : Promise.resolve(null)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const { data: historialCambios = [], isLoading: isLoadingHistorial } = useQuery({
    queryKey: ["proyecto-historial", id],
    queryFn: () => getHistorialProyectoById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
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

  const reabrirMutation = useMutation({
    mutationFn: (proyectoId: string) => reabrirProyecto(proyectoId),
    onSuccess: async (_, proyectoId) => {
      await qc.invalidateQueries({ queryKey: ["proyectos"] });
      await qc.invalidateQueries({ queryKey: ["proyecto", proyectoId] });
      setSuccessMessage("Proyecto reabierto con éxito.");
      setShowSuccess(true);
    },
  });

  const prorrogaMutation = useMutation({
    mutationFn: (motivo: string) => prorrogarProyecto(String(id), motivo),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["proyectos"] }),
        qc.invalidateQueries({ queryKey: ["proyecto", id] }),
        qc.invalidateQueries({ queryKey: ["proyecto-historial", id] }),
      ]);
      setMotivoProrroga("");
      setProrrogaError("");
      setSuccessMessage("Prórroga registrada con éxito.");
      setShowSuccess(true);
    },
    onError: (error) => {
      const fields = mapFieldErrors(error, ["motivo"]);
      setProrrogaError(fields.motivo || getErrorMessage(error, "Lo sentimos, no pudimos registrar la prórroga. Verifique los datos e intente nuevamente."));
    },
    onSettled: () => { prorrogaSubmitting.current = false; },
  });

  if (isLoading) return <LoadingSkeleton variant="detail" label="Cargando..." />;
  if (!data) return <p className="text-slate-500">No se encontró el proyecto.</p>;

  const formatFecha = (fecha?: string | null) => {
    if (!fecha) return "-";
    const date = new Date(`${fecha}T00:00:00`);
    return date.toLocaleDateString("es-AR");
  };

  const investigadorCoordinador = data.investigadores?.find((inv) => inv.es_coordinador);
  const coordinador = investigadorCoordinador
    ? `${investigadorCoordinador.nombre_apellido}${investigadorCoordinador.activo === false ? " (inactivo, asignación conservada)" : ""}`
    : "-";

  const investigadores = data.investigadores?.length
    ? data.investigadores
        .filter((inv) => !inv.es_coordinador)
        .map((inv) => inv.nombre_apellido)
        .join(", ") || "-"
    : "-";

  const becarios = data.becarios?.length
    ? data.becarios.map((a) => a.nombre_apellido).join(", ")
    : "-";

  const estaCerrado = data.cerrado === true;
  const estaInactivo = data.activo === false || !!data.deleted_at;

  const formatHistorialValue = (
    item: { campo?: string },
    value: unknown
  ) => {
    if (value === null || value === undefined || value === "") return "-";

    const asNumber =
      typeof value === "number"
        ? value
        : typeof value === "string" && value.trim() !== ""
          ? Number(value)
          : NaN;

    switch (item.campo) {
      case "tipo_proyecto_id":
        return tiposProyecto.find((tipo) => tipo.id === asNumber)?.nombre ?? String(value);
      case "fuente_financiamiento_id":
        return fuentes.find((fuente) => fuente.id === asNumber)?.nombre ?? String(value);
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-2">
          <h2 className="text-2xl md:text-3xl font-semibold leading-none">
            {data.nombreProyecto}
          </h2>

          <span
            className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
              estaCerrado
                ? "border-amber-200 bg-amber-50 text-amber-700"
                : estaInactivo ? "border-slate-200 bg-slate-50 text-slate-600" : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            {estaCerrado ? "Cerrado" : estaInactivo ? "Inactivo" : "Activo"}
          </span>
        </div>

        <div className="ml-auto flex flex-wrap justify-end gap-2">
          {isGestor() && data.id && <Button size="sm" variant="secondary" onClick={() => navigate(`/informes/pid/nuevo?proyectoId=${data.id}`, { state: { projectName: data.nombreProyecto } })}>Registrar Informe</Button>}
          {puedeEditar && (estaCerrado || estaInactivo) && data.id && (!data.fechaFinProrrogada || data.fechaFinProrrogada > getLocalTodayIso()) ? (
            <Button
              size="sm"
              onClick={() => reabrirMutation.mutate(String(data.id))}
              disabled={reabrirMutation.isPending}
             loading={reabrirMutation.isPending}
             loadingText="Reabriendo..."
           >
              {reabrirMutation.isPending ? "Reabriendo..." : "Reabrir"}
            </Button>
          ) : null}

          {puedeEditar && !estaInactivo && !estaCerrado ? (
            <Button
              size="sm"
              onClick={() => navigate(`/proyectos/${data.id}/editar`)}
            >
              Editar
            </Button>
          ) : null}
        </div>
      </div>

      <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <div className="space-y-3 text-sm text-slate-500 md:text-base">
          <p>
            <span className="font-semibold text-slate-800">Código del proyecto:</span>{" "}
            {data.codigoProyecto}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Coordinador:</span>{" "}
            {coordinador}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Investigadores:</span>{" "}
            {investigadores}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Becarios:</span>{" "}
            {becarios}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Descripción:</span>{" "}
            {data.descripcionProyecto || "-"}
          </p>

          <p className="whitespace-pre-wrap">
            <span className="font-semibold text-slate-800">Logros obtenidos:</span>{" "}
            {data.logrosObtenidos || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Dificultades del proyecto:</span>{" "}
            {data.dificultadesProyecto || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Tipo de proyecto:</span>{" "}
            {data.tipoProyectoNombre || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Fuente de financiamiento:</span>{" "}
            {data.fuenteFinanciamientoNombre || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Grupo UTN:</span>{" "}
            {data.grupoUtnNombre || "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Monto destinado:</span>{" "}
            {data.montoDestinado !== undefined && data.montoDestinado !== null
              ? data.montoDestinado
              : "-"}
          </p>

          <p>
            <span className="font-semibold text-slate-800">Fecha de inicio:</span>{" "}
            {formatFecha(data.fechaInicio)}
          </p>

          {data.fechaFinProrrogada && <p><span className="font-semibold text-slate-800">Fecha final original:</span>{" "}{formatFecha(data.fechaFinOriginal)}</p>}
          {data.fechaFinProrrogada && estaCerrado && <p><span className="font-semibold text-slate-800">Fecha final aprobada por prórroga:</span>{" "}{formatFecha(data.fechaFinProrrogada)}</p>}
          <p>
            <span className="font-semibold text-slate-800">{estaCerrado ? "Fecha de cierre real:" : data.fechaFinProrrogada ? "Fecha final vigente (con prórroga):" : "Fecha final vigente:"}</span>{" "}
            {formatFecha(data.fechaFinalizacion)}
          </p>
          {data.fechaFinProrrogada && <>
            <p><span className="font-semibold text-slate-800">Justificación de la prórroga:</span>{" "}{data.prorrogaMotivo}</p>
            <p><span className="font-semibold text-slate-800">Decisión de Prorrogación:</span>{" "}Aprobada por {data.prorrogaByNombre || "-"} el {formatFechaHora(data.prorrogaAt)}</p>
          </>}
        </div>
      </article>

      {puedeEditar && data.activo !== false && !data.deleted_at && !data.fechaFinProrrogada && data.fechaFinOriginal && (
        <form noValidate className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm" onSubmit={(event) => {
          event.preventDefault();
          if (motivoProrroga.trim().length < 10) {
            setProrrogaError("Ingrese una justificación de al menos 10 caracteres.");
            return;
          }
          if (prorrogaSubmitting.current) return;
          prorrogaSubmitting.current = true;
          prorrogaMutation.mutate(motivoProrroga.trim());
        }}>
          <h3 className="text-lg font-semibold text-slate-800">Prórroga de 12 meses</h3>
          <p className="mt-1 text-sm text-slate-500">Se agregará una única prórroga al período original. Puede registrarse después del vencimiento.</p>
          <label htmlFor="motivo-prorroga" className="mt-4 block text-sm font-medium text-slate-700">Justificación</label>
          <textarea id="motivo-prorroga" className="input mt-2 w-full" value={motivoProrroga} maxLength={2000} aria-invalid={Boolean(prorrogaError)} aria-describedby={prorrogaError ? "motivo-prorroga-error" : undefined} onChange={(event) => {setMotivoProrroga(event.target.value); setProrrogaError("");}} />
          {prorrogaError && <p id="motivo-prorroga-error" role="alert" className="mt-2 text-sm text-rose-700">{prorrogaError}</p>}
          <div className="mt-4"><Button type="submit" size="sm" loading={prorrogaMutation.isPending} disabled={prorrogaMutation.isPending}>Registrar prórroga</Button></div>
        </form>
      )}

      <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
          <p className="mt-1 text-xs text-slate-500">{data.nombreProyecto}</p>
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
        subtitle={data.nombreProyecto}
        items={historialCambios}
        isLoading={isLoadingHistorial}
        updatedAt={data.updated_at}
        updatedByName={data.updated_by_nombre}
        formatItemValue={(item, value) => formatHistorialValue(item, value)}
        formatItemPresentation={(item) =>
          formatProyectoRelationHistoryEntry(item, data)
        }
      />

      <div className="flex justify-start pt-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => navigateBackFromMemoriaContext(navigate, location, "/proyectos")}
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
