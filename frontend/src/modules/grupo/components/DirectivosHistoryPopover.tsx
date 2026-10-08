import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, History, RefreshCw, X } from "lucide-react";
import { Popover } from "radix-ui";
import { useCambiosDirectivos, usePeriodosDirectivos } from "@/modules/grupo/hooks/useDirectivos";
import { useHistorialGrupo } from "@/modules/grupo/hooks/useUct";
import { formatFechaHora } from "@/utils/dateTime";

const PAGE_SIZE = 3;
const FIELD_LABELS: Record<string, string> = {
  nombre_unidad_academica: "Facultad Regional",
  nombre_sigla_grupo: "Nombre y Sigla",
  mail: "Correo electrónico",
  objetivo_desarrollo: "Objetivos y desarrollo",
};

type Props = {
  grupoId: number;
};

export default function DirectivosHistoryPopover({ grupoId }: Props) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [view, setView] = useState<"grupo" | "directivos" | "cambios">("grupo");
  const {
    data: periodos = [],
    isLoading: isLoadingDirectivos,
    isError: isErrorDirectivos,
    isFetching: isFetchingDirectivos,
    refetch: refetchDirectivos,
  } = usePeriodosDirectivos(grupoId, open && view === "directivos");
  const {
    data: cambios = [],
    isLoading: isLoadingGrupo,
    isError: isErrorGrupo,
    isFetching: isFetchingGrupo,
    refetch: refetchGrupo,
  } = useHistorialGrupo(grupoId, open && view === "grupo");
  const {
    data: cambiosDirectivos,
    isLoading: isLoadingCambiosDirectivos,
    isError: isErrorCambiosDirectivos,
    isFetching: isFetchingCambiosDirectivos,
    refetch: refetchCambiosDirectivos,
  } = useCambiosDirectivos(grupoId, page, open && view === "cambios");

  const isLoading = view === "grupo" ? isLoadingGrupo : view === "directivos" ? isLoadingDirectivos : isLoadingCambiosDirectivos || isFetchingCambiosDirectivos;
  const isError = view === "grupo" ? isErrorGrupo : view === "directivos" ? isErrorDirectivos : isErrorCambiosDirectivos;
  const isFetching = view === "grupo" ? isFetchingGrupo : view === "directivos" ? isFetchingDirectivos : isFetchingCambiosDirectivos;
  const items = view === "grupo" ? cambios : view === "directivos" ? periodos : cambiosDirectivos?.items ?? [];

  const totalPages = Math.max(1, Math.ceil((view === "cambios" ? cambiosDirectivos?.total ?? 0 : items.length) / PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen) {
      setView("grupo");
      setPage(1);
    }
  }

  function selectView(nextView: "grupo" | "directivos" | "cambios") {
    setView(nextView);
    setPage(1);
  }

  return (
    <Popover.Root modal={false} open={open} onOpenChange={handleOpenChange}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="inline-flex h-8 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2"
          aria-label="Ver historial del grupo"
        >
          <History className="h-4 w-4" aria-hidden="true" />
          Historial Grupo
        </button>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={8}
          collisionPadding={16}
          className="z-50 w-[min(28rem,calc(100vw-2rem))] rounded-lg border border-slate-200 bg-white shadow-xl outline-none"
          aria-label="Historial del grupo"
        >
          <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Historial del grupo
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Cambios institucionales, cambios del equipo y períodos directivos.
              </p>
            </div>
            <Popover.Close asChild>
              <button
                type="button"
                className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
                title="Cerrar historial"
                aria-label="Cerrar historial"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </Popover.Close>
          </div>

          <div className="grid grid-cols-3 gap-1 border-b border-slate-200 px-4 py-3" role="group" aria-label="Tipo de historial">
            <button
              type="button"
              aria-pressed={view === "grupo"}
              onClick={() => selectView("grupo")}
              className={`rounded-md px-2 py-1.5 text-xs font-medium sm:text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 ${view === "grupo" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              Cambios del grupo
            </button>
            <button
              type="button"
              aria-pressed={view === "cambios"}
              onClick={() => selectView("cambios")}
              className={`rounded-md px-1 py-1.5 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 ${view === "cambios" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              Cambios directivos
            </button>
            <button
              type="button"
              aria-pressed={view === "directivos"}
              onClick={() => selectView("directivos")}
              className={`rounded-md px-1 py-1.5 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 ${view === "directivos" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              Períodos directivos
            </button>
          </div>

          <div className="min-h-40 px-4 py-3" aria-live="polite">
            {isLoading && <HistoryLoading />}

            {!isLoading && isError && (
              <div className="grid min-h-32 place-items-center text-center">
                <div>
                  <p className="text-sm text-slate-700">
                    Lo sentimos, no pudimos recuperar el historial. Intente
                    nuevamente.
                  </p>
                  <button
                    type="button"
                    onClick={() => view === "grupo" ? refetchGrupo() : view === "directivos" ? refetchDirectivos() : refetchCambiosDirectivos()}
                    disabled={isFetching}
                    className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-slate-900 hover:underline disabled:opacity-50"
                  >
                    <RefreshCw
                      className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
                      aria-hidden="true"
                    />
                    Reintentar
                  </button>
                </div>
              </div>
            )}

            {!isLoading && !isError && items.length === 0 && (
              <div className="grid min-h-32 place-items-center text-center text-sm text-slate-500">
                {view === "grupo"
                  ? "Todavía no hay cambios del grupo registrados."
                  : view === "directivos" ? "Todavía no hay períodos directivos registrados." : "Todavía no hay cambios de directivos registrados."}
              </div>
            )}

            {!isLoading && !isError && items.length > (view === "cambios" ? 0 : (page - 1) * PAGE_SIZE) && (
              <ol className="divide-y divide-slate-100">
                {view === "grupo" ? cambios.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((cambio) => (
                  <li key={cambio.id} className="py-3 first:pt-1 last:pb-1">
                    <p className="text-sm font-semibold text-slate-900">
                      {FIELD_LABELS[cambio.campo] ?? cambio.campo.replace(/_/g, " ")}
                    </p>
                    <p className="mt-1 text-sm text-slate-600 break-words">
                      <span className="font-medium">Anterior:</span> {cambio.valor_anterior || "-"}
                    </p>
                    <p className="mt-0.5 text-sm text-slate-600 break-words">
                      <span className="font-medium">Nuevo:</span> {cambio.valor_nuevo || "-"}
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      {formatFechaHora(cambio.fecha_cambio)} · Por {cambio.usuario_nombre || "Usuario no disponible"}
                    </p>
                  </li>
                )) : view === "directivos" ? periodos.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((periodo) => (
                  <li key={periodo.id} className="py-3 first:pt-1 last:pb-1">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-900">
                          {periodo.nombre_apellido}
                        </p>
                        <p className="mt-0.5 text-sm text-slate-600">
                          {periodo.cargo}
                        </p>
                      </div>
                      <span className="inline-flex shrink-0 items-center gap-1.5 text-xs text-slate-500">
                        <span
                          className={`h-2 w-2 rounded-full ${periodo.fecha_fin ? "bg-slate-400" : "bg-emerald-500"}`}
                          aria-hidden="true"
                        />
                        {periodo.fecha_fin ? "Finalizado" : "Actual"}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      {formatDateOnly(periodo.fecha_inicio)} a {periodo.fecha_fin
                        ? formatDateOnly(periodo.fecha_fin)
                        : "la actualidad"}
                    </p>
                  </li>
                )) : cambiosDirectivos?.items.map((evento) => {
                  const mandato = typeof evento.valor_nuevo === "object" && evento.valor_nuevo !== null ? evento.valor_nuevo : null;
                  return (
                    <li key={evento.id} className="py-3 first:pt-1 last:pb-1">
                      <p className="text-sm font-semibold text-slate-900">
                        {mandato ? `${mandato.accion === "asignado" ? "Asignación" : "Finalización"} de ${mandato.detalle.cargo}` : "Nombre del directivo"}
                      </p>
                      {mandato ? (
                        <p className="mt-1 text-sm text-slate-600 break-words">
                          {mandato.detalle.nombre_apellido} · Inicio: {formatDateOnly(mandato.detalle.fecha_inicio)}
                          {mandato.detalle.fecha_fin ? ` · Fin: ${formatDateOnly(mandato.detalle.fecha_fin)}` : ""}
                        </p>
                      ) : (
                        <p className="mt-1 text-sm text-slate-600 break-words">
                          {evento.valor_anterior || "-"} → {typeof evento.valor_nuevo === "string" ? evento.valor_nuevo : "-"}
                        </p>
                      )}
                      <p className="mt-2 text-xs text-slate-500">
                        {formatFechaHora(evento.fecha_cambio)} · Por {evento.usuario_nombre || "Usuario no disponible"}
                      </p>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>

          {!isLoading && !isError && totalPages > 1 && (
            <div className="flex h-11 items-center justify-between border-t border-slate-200 px-3">
              <span className="text-xs text-slate-500">
                Página {page} de {totalPages}
              </span>
              <div className="flex items-center gap-1">
                <PageButton
                  label="Página anterior"
                  disabled={page === 1}
                  onClick={() => setPage((current) => current - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </PageButton>
                <PageButton
                  label="Página siguiente"
                  disabled={page === totalPages}
                  onClick={() => setPage((current) => current + 1)}
                >
                  <ChevronRight className="h-4 w-4" />
                </PageButton>
              </div>
            </div>
          )}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function HistoryLoading() {
  return (
    <div className="space-y-3" aria-label="Cargando historial">
      {[0, 1, 2].map((item) => (
        <div key={item} className="space-y-2 border-b border-slate-100 pb-3 last:border-0">
          <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
          <div className="h-3 w-1/3 animate-pulse rounded bg-slate-100" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

function PageButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="grid h-8 w-8 place-items-center rounded-md text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-35"
    >
      {children}
    </button>
  );
}

function formatDateOnly(value: string) {
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;
  return `${day}/${month}/${year}`;
}
