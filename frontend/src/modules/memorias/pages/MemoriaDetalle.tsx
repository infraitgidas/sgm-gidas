import LoadingSkeleton from "@/components/LoadingSkeleton";
import MemoriaPeriodoForm from "@/modules/memorias/components/MemoriaPeriodoForm";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import SuccessToast from "@/components/SuccessToast";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import {
  cambiarEstadoMemoria,
  getMemoriaById,
  getHistorialMemoria,
  reabrirMemoria,
  type Memoria,
  type MemoriaEstado,
} from "@/modules/memorias/services/memoriasService";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";

export default function MemoriaDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAdmin, isGestor } = useAuth();

  const puedeEditar = isAdmin() || isGestor();
  const puedeReabrir = isAdmin() || isGestor();

  const [editandoPeriodo, setEditandoPeriodo] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [estadoPendiente, setEstadoPendiente] = useState<MemoriaEstado | null>(null);
  const [showReopenConfirm, setShowReopenConfirm] = useState(false);

  const { data: memoria, isLoading, isError } = useQuery<Memoria | null>({
    queryKey: ["memoria", id],
    queryFn: () => getMemoriaById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const { data: historial = [], isLoading: cargandoHistorial, isError: errorHistorial } = useQuery({
    queryKey: ["memoria-historial", id],
    queryFn: () => getHistorialMemoria(Number(id)),
    enabled: !!id,
  });

  useEffect(() => {
    if (location.state?.successMessage) {
      setSuccessMessage(location.state.successMessage);
      setShowSuccess(true);
      navigate(location.pathname, { replace: true });
    }
  }, [location.pathname, location.state, navigate]);

  const handleMutationError = (error: unknown, fallback: string) => {
    setErrorMessage(getErrorMessage(error, fallback));
    setShowError(true);
  };

  const { mutateAsync: actualizarEstado, isPending: isChangingState } = useMutation({
    mutationFn: (estado: MemoriaEstado) =>
      cambiarEstadoMemoria(Number(id), {
        estado,
        fecha_cierre:
          estado === "cerrada" ? new Date().toISOString().slice(0, 19) : undefined,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["memorias"] }),
        queryClient.invalidateQueries({ queryKey: ["memoria", id] }),
        queryClient.invalidateQueries({ queryKey: ["memoria-historial", id] }),
      ]);

      setSuccessMessage("Estado de la memoria actualizado con éxito.");
      setShowSuccess(true);
      setEstadoPendiente(null);
    },
    onError: (error) => {
      setEstadoPendiente(null);
      handleMutationError(
        error,
        "Lo sentimos, no pudimos guardar los cambios. Intente nuevamente."
      );
    },
  });

  const { mutateAsync: reabrir, isPending: isReopening } = useMutation({
    mutationFn: () =>
      reabrirMemoria(Number(id), {
        fecha_apertura: new Date().toISOString().slice(0, 19),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["memorias"] }),
        queryClient.invalidateQueries({ queryKey: ["memoria", id] }),
        queryClient.invalidateQueries({ queryKey: ["memoria-historial", id] }),
      ]);
      setSuccessMessage("Memoria reabierta con éxito.");
      setShowSuccess(true);
      setShowReopenConfirm(false);
    },
    onError: (error) => {
      setShowReopenConfirm(false);
      handleMutationError(
        error,
        "Lo sentimos, no pudimos guardar los cambios. Intente nuevamente."
      );
    },
  });

  const versionActual = memoria?.version_actual;

  const estadosDisponibles = useMemo(() => {
    if (!versionActual?.estado) return [];

    if (versionActual.estado === "abierta") {
      return ["en revision", "cerrada"] as MemoriaEstado[];
    }

    if (versionActual.estado === "en revision") {
      return ["abierta", "cerrada"] as MemoriaEstado[];
    }

    return [] as MemoriaEstado[];
  }, [versionActual?.estado]);

  if (isLoading) {
    return <LoadingSkeleton variant="detail" label="Cargando memoria..." />;
  }

  if (isError) return <p role="alert">Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>;

  if (!memoria || !versionActual) {
    return <p className="text-slate-500">No se encontró la memoria.</p>;
  }

  const puedeCorregirPeriodo = (isAdmin() || isGestor()) && !memoria.deleted_at &&
    !(memoria.versiones || []).some((v) => v.estado === "cerrada" || !!v.fecha_cierre);
  const snapshotDisponible = versionActual.estado === "cerrada";

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              Memoria {formatFecha(memoria.periodo_inicio)}–{formatFecha(memoria.periodo_fin)}
            </h2>

            <span
              className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
                memoria.deleted_at
                  ? "border-rose-200 bg-rose-50 text-rose-700"
                  : versionActual.estado === "cerrada"
                    ? "border-amber-200 bg-amber-50 text-amber-700"
                    : "border-emerald-200 bg-emerald-50 text-emerald-700"
              }`}
            >
              {memoria.deleted_at ? "INACTIVA" : versionActual.estado.toUpperCase()}
            </span>
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            {puedeCorregirPeriodo && !editandoPeriodo && <Button size="sm" variant="secondary" onClick={() => setEditandoPeriodo(true)}>Editar período</Button>}
            <Button
              variant="secondary"
              size="sm"
              disabled={!snapshotDisponible}
              onClick={() =>
                navigate(`/memorias/${memoria.id}/versiones/${versionActual.id}`)
              }
            >
              {snapshotDisponible ? "Ver elementos registrados" : "Snapshot pendiente"}
            </Button>

            {puedeEditar &&
              !memoria.deleted_at &&
              estadosDisponibles.map((estado) => (
                <Button
                  key={estado}
                  size="sm"
                  variant="secondary"
                  onClick={() => setEstadoPendiente(estado)}
                >
                  {estado === "cerrada"
                    ? "Cerrar memoria"
                    : estado === "en revision"
                      ? "Enviar a revisión"
                      : "Volver a abierta"}
                </Button>
              ))}

            {puedeReabrir &&
              !memoria.deleted_at &&
              versionActual.estado === "cerrada" && (
                <Button size="sm" onClick={() => setShowReopenConfirm(true)}>
                  Reabrir
                </Button>
              )}
          </div>
        </div>

        {!memoria.grupo_utn_id && <p role="status">Esta memoria anterior requiere una asociación explícita a una UCT. Las versiones cerradas se conservan sin reconstruir su historia.</p>}
        {editandoPeriodo && puedeCorregirPeriodo && <article className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-semibold">Editar período</h3>
          <MemoriaPeriodoForm memoria={memoria} onCancel={() => setEditandoPeriodo(false)} onSaved={() => {
            setEditandoPeriodo(false);
            navigate(`/memorias/${memoria.id}`, { replace: true, state: { successMessage: "Período de la memoria actualizado con éxito." } });
          }} />
        </article>}
        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">
              Datos de la memoria
            </h3>
          </div>

          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p><span className="font-semibold text-slate-800">UCT:</span> {memoria.grupo_utn_nombre || "Pendiente de asociar"}</p>
            <p>
              El período define qué información integra la memoria. Su estado
              permanece abierto hasta que un gestor o administrador la cierre.
            </p>
            <p>
              <span className="font-semibold text-slate-800">Período de inicio:</span>{" "}
              {formatFecha(memoria.periodo_inicio)}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Período de fin:</span>{" "}
              {formatFecha(memoria.periodo_fin)}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Cantidad de versiones:</span>{" "}
              {memoria.cantidad_versiones}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Creada por:</span>{" "}
              {memoria.created_by_nombre || "-"}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Fecha de creación:</span>{" "}
              {formatFechaHora(memoria.created_at)}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Versión actual</h3>
          </div>

          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Número de versión:</span>{" "}
              {versionActual.numero_version}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Estado:</span>{" "}
              {versionActual.estado}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Fecha de apertura:</span>{" "}
              {formatFechaHora(versionActual.fecha_apertura)}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Fecha de cierre:</span>{" "}
              {formatFechaHora(versionActual.fecha_cierre)}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Última actualización:</span>{" "}
              {formatFechaHora(versionActual.updated_at)}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Actualizada por:</span>{" "}
              {versionActual.updated_by_nombre || "-"}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">
              Historial de versiones
            </h3>
          </div>

          <div className="space-y-3">
            {(memoria.versiones || []).map((version) => (
              <div
                key={version.id}
                className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-1 text-sm text-slate-500">
                  <p>
                    <span className="font-semibold text-slate-800">Versión:</span>{" "}
                    {version.numero_version}
                  </p>
                  <p>
                    <span className="font-semibold text-slate-800">Estado:</span>{" "}
                    {version.estado}
                  </p>
                  <p>
                    <span className="font-semibold text-slate-800">Apertura:</span>{" "}
                    {formatFechaHora(version.fecha_apertura)}
                  </p>
                  <p>
                    <span className="font-semibold text-slate-800">Cierre:</span>{" "}
                    {formatFechaHora(version.fecha_cierre)}
                  </p>
                </div>

                <div className="flex justify-start md:justify-end">
                  {version.estado === "cerrada" ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        navigate(`/memorias/${memoria.id}/versiones/${version.id}`)
                      }
                    >
                      Ver elementos
                    </Button>
                  ) : (
                    <Button variant="secondary" size="sm" disabled>
                      Snapshot pendiente
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-semibold">Auditoría</h3>
          <p className="text-sm text-slate-500">Creada: {formatFechaHora(memoria.created_at)} por {memoria.created_by_nombre || "-"}</p>
          <p className="text-sm text-slate-500">Actualizada: {formatFechaHora(memoria.updated_at)} por {memoria.updated_by_nombre || "-"}</p>
          {memoria.deleted_at && <p className="text-sm text-slate-500">Baja: {formatFechaHora(memoria.deleted_at)} por {memoria.deleted_by_nombre || "-"}</p>}
        </article>
        {errorHistorial ? <p role="alert">Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</p> :
          <HistorialCambiosCard
            items={historial.map((item) => ({
              ...item,
              campo: item.campo === "grupo_utn_id" ? "UCT" : item.campo,
            }))}
            isLoading={cargandoHistorial}
            pageSize={3}
          />}
        <div className="flex justify-start pt-4">
          <Button variant="secondary" size="sm" onClick={() => navigate("/memorias")}>
            Volver
          </Button>
        </div>
      </section>

      <ConfirmDialog
        open={!!estadoPendiente}
        title="Cambiar estado de memoria"
        message={`Cambiar la memoria al estado "${estadoPendiente || ""}"?`}
        items={[`Versión actual: ${versionActual.numero_version}`]}
        onCancel={() => setEstadoPendiente(null)}
        onConfirm={() =>
          estadoPendiente
            ? actualizarEstado(estadoPendiente)
            : Promise.resolve(undefined)
        }
        confirmText={isChangingState ? "Actualizando..." : "Confirmar"}
       loadingText="Actualizando..."
     />

      <ConfirmDialog
        open={showReopenConfirm}
        title="Reabrir memoria"
        message="Se creará una nueva versión abierta a partir de la actual. ¿Desea continuar?"
        items={[`Memoria ${memoria.id}`]}
        onCancel={() => setShowReopenConfirm(false)}
        onConfirm={() => reabrir()}
        confirmText={isReopening ? "Reabriendo..." : "Confirmar"}
       loadingText="Reabriendo..."
     />

      <SuccessToast
        open={showSuccess}
        message={successMessage}
        onClose={() => setShowSuccess(false)}
      />

      <SuccessToast
        open={showError}
        message={errorMessage}
        onClose={() => setShowError(false)}
        variant="error"
      />
    </>
  );
}
