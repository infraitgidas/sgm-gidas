import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { Eye, RotateCcw, LockKeyhole, Send } from "lucide-react";

import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import SuccessToast from "@/components/SuccessToast";
import Table, {
  TableActionButton,
  TableActions,
  TableFilterChip,
  TableRowActionButton,
  TableSearch,
  TableToolbar,
  type TableColumn,
} from "@/components/Table";
import TableFilterSelect from "@/components/TableFilterSelect";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import {
  deleteMemoria,
  cambiarEstadoMemoria,
  reabrirMemoria,
  getMemoriaById,
  getMemorias,
  type Memoria,
  type MemoriaActivosFilter,
  type MemoriaEstado,
} from "@/modules/memorias/services/memoriasService";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";

const ITEMS_PER_PAGE = 9;

const memoriaTitle = (memoria: Memoria) =>
  `Memoria ${formatFecha(memoria.periodo_inicio)}–${formatFecha(memoria.periodo_fin)}`;

const estadoLabel: Record<MemoriaEstado, string> = {
  abierta: "Abierta",
  "en revision": "En revisión",
  cerrada: "Cerrada",
};

function EstadoVersion({ estado }: { estado: MemoriaEstado }) {
  const color = estado === "cerrada"
    ? "bg-violet-50 text-violet-700"
    : estado === "en revision"
      ? "bg-orange-50 text-orange-700"
      : "bg-amber-50 text-amber-700";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${color}`}>
      {estadoLabel[estado] ?? estado}
    </span>
  );
}

function MemoriaVersions({ memoria, puedeCrear, onFeedback }: {
  memoria: Memoria;
  puedeCrear: boolean;
  onFeedback: (mensaje: string, error: boolean) => void;
}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [accion, setAccion] = useState<"reabrir" | "cerrada" | "en revision" | null>(null);
  const mutation = useMutation({
    mutationFn: async () => {
      if (!accion || !puedeCrear || memoria.deleted_at || memoria.activo === false) return;
      if (accion === "reabrir") await reabrirMemoria(memoria.id);
      else await cambiarEstadoMemoria(memoria.id, { estado: accion });
    },
    onSuccess: async () => {
      setAccion(null);
      onFeedback("Memoria actualizada con éxito.", false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["memorias"] }),
        queryClient.invalidateQueries({ queryKey: ["memoria"] }),
        queryClient.invalidateQueries({ queryKey: ["memoria-historial"] }),
      ]);
    },
    onError: (error) => {
      setAccion(null);
      onFeedback(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."), true);
    },
  });
  const detail = useQuery({
    queryKey: ["memoria", memoria.id],
    queryFn: () => getMemoriaById(memoria.id),
  });
  if (detail.isLoading) return <LoadingSkeleton variant="compact" label="Cargando versiones…" />;
  if (detail.isError || !detail.data) {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-rose-700">
        <span>Lo sentimos, no pudimos recuperar las versiones. Intente nuevamente.</span>
        <TableActionButton onClick={() => detail.refetch()}>Reintentar</TableActionButton>
      </div>
    );
  }
  const memoriaActualizada = detail.data;
  const versiones = memoriaActualizada.versiones ?? [];
  if (!versiones.length) return <p className="text-sm text-slate-500">No hay versiones registradas.</p>;
  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Versiones de la memoria</h3>
      <ul className="space-y-2">
        {versiones.map((version) => {
          const actual = version.id === memoriaActualizada.version_actual_id;
          const editable = actual && !memoriaActualizada.deleted_at && memoriaActualizada.activo !== false && puedeCrear;
          return (
            <li key={version.id} className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-medium text-slate-900">Versión {version.numero_version}</span>
                <EstadoVersion estado={version.estado} />
                {actual && <span className="text-xs text-slate-500">Actual</span>}
                <span className="basis-full text-xs text-slate-500">
                  Apertura: {formatFechaHora(version.fecha_apertura)}
                  {version.fecha_cierre && ` · Cierre: ${formatFechaHora(version.fecha_cierre)}`}
                </span>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <TableActionButton title="Ver detalle" aria-label={`Ver detalle de la versión ${version.numero_version}`} onClick={() => navigate(version.estado === "cerrada" ? `/memorias/${memoria.id}/versiones/${version.id}` : `/memorias/${memoria.id}`)}>
                  <Eye aria-hidden="true" className="h-4 w-4" />
                </TableActionButton>
                {puedeCrear && <>
                  <TableActionButton title="Reabrir: crear nueva versión" aria-label={`Reabrir la versión ${version.numero_version}`} disabled={!editable || version.estado !== "cerrada" || mutation.isPending} onClick={() => setAccion("reabrir")}>
                    <RotateCcw aria-hidden="true" className="h-4 w-4" />
                  </TableActionButton>
                  <TableActionButton title="Cerrar memoria" aria-label={`Cerrar la versión ${version.numero_version}`} disabled={!editable || version.estado === "cerrada" || mutation.isPending} onClick={() => setAccion("cerrada")}>
                    <LockKeyhole aria-hidden="true" className="h-4 w-4" />
                  </TableActionButton>
                  <TableActionButton title="Enviar a revisión" aria-label={`Enviar a revisión la versión ${version.numero_version}`} disabled={!editable || version.estado !== "abierta" || mutation.isPending} onClick={() => setAccion("en revision")}>
                    <Send aria-hidden="true" className="h-4 w-4" />
                  </TableActionButton>
                </>}
              </div>
            </li>
          );
        })}
      </ul>
      <ConfirmDialog
        open={accion !== null}
        title={accion === "reabrir" ? "Reabrir memoria" : accion === "cerrada" ? "Cerrar memoria" : "Enviar a revisión"}
        message={accion === "reabrir" ? "Se creará una nueva versión abierta. La versión cerrada conservará sus datos. ¿Desea continuar?" : accion === "cerrada" ? "Se congelarán los datos del período en esta versión. ¿Desea cerrar la memoria?" : "¿Desea enviar la versión actual a revisión?"}
        onCancel={() => { if (!mutation.isPending) setAccion(null); }}
        onConfirm={() => mutation.mutateAsync()}
        loadingText="Guardando..."
      />
    </div>
  );
}

export default function MemoriasHome() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAdmin, isGestor } = useAuth();
  const puedeCrear = isAdmin() || isGestor();
  const puedeEliminar = isAdmin();

  const [estado, setEstado] = useState<MemoriaActivosFilter>("true");
  const [estadoVersion, setEstadoVersion] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(() => new Set());
  const [pendingDelete, setPendingDelete] = useState<Memoria | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const memoriasQuery = useQuery({
    queryKey: ["memorias", estado],
    queryFn: () => getMemorias(estado),
  });
  const memorias = memoriasQuery.data ?? [];

  const filteredList = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase("es");
    return memorias.filter((memoria) => {
      if (estadoVersion && memoria.version_actual?.estado !== estadoVersion) return false;
      if (!query) return true;
      return [
        memoria.grupo_utn_nombre,
        memoria.periodo_inicio,
        memoria.periodo_fin,
        memoria.version_actual?.estado,
        memoria.version_actual?.numero_version,
      ].some((value) => String(value ?? "").toLocaleLowerCase("es").includes(query));
    });
  }, [memorias, searchQuery, estadoVersion]);

  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const paginatedItems = filteredList.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  useEffect(() => {
    setPage(1);
    setExpandedRows(new Set());
  }, [estado, estadoVersion, searchQuery]);

  useEffect(() => {
    if (page > Math.max(totalPages, 1)) setPage(Math.max(totalPages, 1));
  }, [page, totalPages]);

  useEffect(() => {
    if (!location.state?.successMessage) return;
    setSuccessMessage(location.state.successMessage);
    setShowSuccess(true);
    navigate(location.pathname, { replace: true });
  }, [location.pathname, location.state, navigate]);

  const { mutateAsync: eliminarMemoria } = useMutation({
    mutationFn: (id: number) => deleteMemoria(id),
  });

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || pendingDelete.activo === false || !puedeEliminar) return;
    try {
      await eliminarMemoria(pendingDelete.id);
      await queryClient.invalidateQueries({ queryKey: ["memorias"] });
      setExpandedRows(new Set());
      setPendingDelete(null);
      setSuccessMessage("Memoria eliminada con éxito.");
      setShowSuccess(true);
    } catch (error) {
      setPendingDelete(null);
      setErrorMessage(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
      setShowError(true);
    }
  };

  const columns: TableColumn<Memoria>[] = [
    {
      id: "periodo",
      header: "Período",
      render: (memoria) => (
        <div>
          <span className="block font-medium text-slate-900">
            {formatFecha(memoria.periodo_inicio)} – {formatFecha(memoria.periodo_fin)}
          </span>
          <span className="mt-0.5 block text-xs text-slate-500">
            {memoria.cantidad_versiones} {memoria.cantidad_versiones === 1 ? "versión" : "versiones"}
          </span>
        </div>
      ),
    },
    { id: "uct", header: "UCT", priority: "secondary", render: (memoria) => memoria.grupo_utn_nombre || "Pendiente de asociar" },
    {
      id: "version",
      header: "Versión actual",
      priority: "tertiary",
      render: (memoria) => memoria.version_actual ? `Versión ${memoria.version_actual.numero_version}` : "-",
    },
    {
      id: "estado",
      header: "Estado",
      render: (memoria) => memoria.deleted_at || memoria.activo === false
        ? <span className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-700"><span aria-hidden="true" className="h-2 w-2 rounded-full bg-rose-500" />Inactiva</span>
        : memoria.version_actual
          ? <EstadoVersion estado={memoria.version_actual.estado} />
          : "-",
    },
    {
      id: "acciones",
      header: "Acciones",
      align: "right",
      render: (memoria) => (
        <TableActions>
          <TableRowActionButton
            action="view"
            aria-label={`Ver detalle de ${memoriaTitle(memoria)}`}
            onClick={() => navigate(`/memorias/${memoria.id}`)}
          />
          {!memoria.deleted_at && memoria.activo !== false && puedeEliminar && (
            <TableRowActionButton
              action="delete"
              aria-label={`Eliminar ${memoriaTitle(memoria)}`}
              onClick={() => setPendingDelete(memoria)}
            />
          )}
        </TableActions>
      ),
    },
  ];

  return (
    <>
      <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold md:text-3xl">Memorias</h2>
            <p className="mt-1 text-sm text-slate-500">Consulte las memorias por período y sus versiones.</p>
          </div>
          {puedeCrear && <Button size="sm" onClick={() => navigate("/memorias/nueva")}>Agregar nuevo</Button>}
        </div>

        <Table
          caption="Listado de memorias por período"
          columns={columns}
          rows={paginatedItems}
          getRowId={(memoria) => memoria.id}
          density="compact"
          loading={memoriasQuery.isLoading}
          refreshing={memoriasQuery.isFetching && !memoriasQuery.isLoading}
          error={memoriasQuery.isError}
          onRetry={() => memoriasQuery.refetch()}
          emptyMessage="No hay memorias que coincidan con los filtros."
          onRowClick={(memoria) => navigate(`/memorias/${memoria.id}`)}
          getRowTitle={(memoria) => `Ver detalle de ${memoriaTitle(memoria)}`}
          isRowExpanded={(memoria) => expandedRows.has(memoria.id)}
          renderExpanded={(memoria) => <MemoriaVersions memoria={memoria} puedeCrear={puedeCrear} onFeedback={(mensaje, error) => {
            if (error) { setErrorMessage(mensaje); setShowError(true); }
            else { setSuccessMessage(mensaje); setShowSuccess(true); }
          }} />}
          onToggleRow={(memoria) => setExpandedRows((current) => {
            const next = new Set(current);
            if (next.has(memoria.id)) next.delete(memoria.id);
            else next.add(memoria.id);
            return next;
          })}
          getExpandLabel={(memoria, expanded) => `${expanded ? "Ocultar" : "Mostrar"} versiones de ${memoriaTitle(memoria)}`}
          page={page}
          totalPages={totalPages}
          totalRecords={filteredList.length}
          onPageChange={(nextPage) => { setExpandedRows(new Set()); setPage(nextPage); }}
          toolbar={
            <TableToolbar>
              <div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center">
                <TableSearch
                  label="Buscar memorias"
                  placeholder="Buscar por UCT, período o versión"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                <div
                  className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent"
                  aria-label="Filtros de memorias"
                >
                  <span className="shrink-0 text-xs font-medium text-slate-500">Estado</span>
                  <TableFilterChip className="shrink-0" active={estado === "true"} onClick={() => setEstado("true")}>Activas</TableFilterChip>
                  <TableFilterChip className="shrink-0" active={estado === "all"} onClick={() => setEstado("all")}>Todas</TableFilterChip>
                  <TableFilterChip className="shrink-0" active={estado === "false"} onClick={() => setEstado("false")}>Inactivas</TableFilterChip>
                  <TableFilterSelect
                    label="Filtrar por estado de versión"
                    placeholder="Todos los estados de versión"
                    value={estadoVersion || undefined}
                    onValueChange={(value) => setEstadoVersion(value ?? "")}
                    options={Object.entries(estadoLabel).map(([value, label]) => ({ value, label }))}
                  />
                </div>
              </div>
            </TableToolbar>
          }
        />

        <ConfirmDialog
          open={Boolean(pendingDelete)}
          title="Eliminar memoria"
          message={`¿Está seguro de eliminar ${pendingDelete ? memoriaTitle(pendingDelete) : "esta memoria"}?`}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
          loadingText="Eliminando..."
        />
      </section>
      <SuccessToast open={showSuccess} message={successMessage} onClose={() => setShowSuccess(false)} />
      <SuccessToast open={showError} message={errorMessage} onClose={() => setShowError(false)} variant="error" />
    </>
  );
}
