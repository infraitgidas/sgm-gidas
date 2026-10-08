import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import MemoriaFilterBanner from "@/components/MemoriaFilterBanner";
import SuccessToast from "@/components/SuccessToast";
import Table, { TableActionButton, TableActions, TableFilterChip, TableRowActionButton, TableSearch, TableToolbar } from "@/components/Table";
import type { TableColumn, TableSortDirection } from "@/components/Table";
import TableFilterSelect from "@/components/TableFilterSelect";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import { buildMemoriaDetailState } from "@/lib/memoriaNavigation";
import { applyMemoriaSectionFilter, getMemoriaSectionFilter } from "@/lib/memoriaSectionFilter";
import { useFuentesFinanciamiento } from "@/modules/catalogos/hooks/useFuenteFinanciamiento";
import { useUct } from "@/modules/grupo/hooks/useUct";
import { useCategoriasErogacion } from "@/modules/recursos/hooks/useCategoriasErogacion";
import { useErogaciones } from "@/modules/recursos/hooks/useErogaciones";
import { useSaldosPorFuente } from "@/modules/recursos/hooks/useSaldosPorFuente";
import { deleteErogaciones, getHistorialErogacionById, getResumenFinanciero, type Erogacion } from "@/modules/recursos/services/erogacionesServices";
import { formatMovimientoHistoryEntry, formatMovimientoMoney, presentMovimientoHistoryItems } from "@/modules/recursos/utils/movimientoHistory";
import { formatFecha, formatFechaHora, getCivilYear } from "@/utils/dateTime";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;
const SOURCES_PER_PAGE = 3;
const initialFilters = { estado: "", tipo: "", fuente: "", categoria: "", anio: "", desde: "", hasta: "" };
const movementLabel = (item: Erogacion) => `Movimiento N.º ${String(item.numero_movimiento).padStart(6, "0")}`;

export default function ErogacionesLanding() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();
  const { uct, isLoading: uctLoading, isError: uctError } = useUct();
  const { fuentes } = useFuentesFinanciamiento();
  const { data: categorias = [] } = useCategoriasErogacion();
  const [filters, setFilters] = useState(initialFilters);
  const [fuenteDashboard, setFuenteDashboard] = useState<string | undefined>();
  const [fuentesPage, setFuentesPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState("fecha");
  const [sortDirection, setSortDirection] = useState<TableSortDirection>("desc");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<Erogacion | null>(null);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const memoriaFilter = useMemo(() => getMemoriaSectionFilter(location.state, "erogaciones"), [location.state]);
  const activos = memoriaFilter || filters.estado === "todos" ? "all" : filters.estado === "inactivos" ? "false" : "true";
  const movimientos = useErogaciones(activos, uct?.id);
  const saldosPorFuente = useSaldosPorFuente(uct?.id);
  const fuentesDashboard = saldosPorFuente.data ?? [];
  const fuenteDashboardActual = fuentesDashboard.some((item) => String(item.fuente_id) === fuenteDashboard)
    ? fuenteDashboard : undefined;
  const saldosPorFuenteVisibles = fuenteDashboardActual
    ? fuentesDashboard.filter((item) => String(item.fuente_id) === fuenteDashboardActual)
    : fuentesDashboard;
  const fuentesTotalPages = Math.max(1, Math.ceil(saldosPorFuenteVisibles.length / SOURCES_PER_PAGE));
  const fuentesCurrentPage = Math.min(fuentesPage, fuentesTotalPages);
  const fuentesPaginadas = saldosPorFuenteVisibles.slice(
    (fuentesCurrentPage - 1) * SOURCES_PER_PAGE,
    fuentesCurrentPage * SOURCES_PER_PAGE,
  );
  const resumen = useQuery({
    queryKey: ["resumen-financiero", uct?.id],
    queryFn: () => getResumenFinanciero(uct!.id),
    enabled: Boolean(uct?.id),
  });
  const scopedList = useMemo(() => applyMemoriaSectionFilter(movimientos.list, memoriaFilter), [movimientos.list, memoriaFilter]);
  const years = useMemo(() => [...new Set(scopedList.map((item) => getCivilYear(item.fecha)))]
    .filter((year): year is number => year !== null).sort((a, b) => b - a), [scopedList]);
  const filteredList = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase("es");
    return scopedList.filter((item) => {
      const searchable = [movementLabel(item), String(item.numero_movimiento), item.fuente?.nombre ?? "", item.categoria_erogacion?.nombre ?? ""];
      return (!query || searchable.some((value) => value.toLocaleLowerCase("es").includes(query)))
        && (!filters.tipo || item.tipo_movimiento === filters.tipo)
        && (!filters.fuente || String(item.fuente_financiamiento_id ?? "") === filters.fuente)
        && (!filters.categoria || String(item.categoria_erogacion_id ?? "") === filters.categoria)
        && (!filters.anio || getCivilYear(item.fecha) === Number(filters.anio))
        && (!filters.desde || item.fecha >= filters.desde)
        && (!filters.hasta || item.fecha <= filters.hasta);
    });
  }, [scopedList, searchQuery, filters]);
  const orderedList = useMemo(() => [...filteredList].sort((a, b) => {
    const direction = sortDirection === "asc" ? 1 : -1;
    const comparison = sortKey === "numero" ? a.numero_movimiento - b.numero_movimiento
      : sortKey === "monto" ? Number(a.monto) - Number(b.monto)
        : a.fecha.localeCompare(b.fecha);
    return direction * (comparison || a.numero_movimiento - b.numero_movimiento);
  }), [filteredList, sortKey, sortDirection]);
  const totalPages = Math.max(1, Math.ceil(orderedList.length / ITEMS_PER_PAGE));
  const paginated = orderedList.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);
  const expandedItem = expandedRow === null ? undefined : scopedList.find((item) => item.id === expandedRow);
  const history = useQuery({
    queryKey: ["movimiento-financiero-historial", expandedItem?.id],
    queryFn: () => getHistorialErogacionById(expandedItem!.id),
    enabled: Boolean(expandedItem),
    staleTime: 5 * 60_000,
  });

  useEffect(() => { setPage(1); setExpandedRow(null); }, [filters, searchQuery]);
  useEffect(() => { if (page > totalPages) setPage(totalPages); }, [page, totalPages]);
  useEffect(() => {
    if (!location.state?.successMessage) return;
    setSuccessMessage(location.state.successMessage);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  const setFilter = (key: keyof typeof initialFilters, value?: string) =>
    setFilters((current) => ({ ...current, [key]: value ?? "" }));

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || !canDeleteRecords()) return;
    try {
      await deleteErogaciones(pendingDelete.id);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["erogaciones"] }),
        queryClient.invalidateQueries({ queryKey: ["resumen-financiero"] }),
        queryClient.invalidateQueries({ queryKey: ["saldos-por-fuente"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      ]);
      setPendingDelete(null);
      setSuccessMessage("Movimiento eliminado con éxito.");
    } catch (error) {
      setPendingDelete(null);
      setErrorMessage(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
    }
  };

  const renderHistory = () => {
    if (history.isLoading) return <LoadingSkeleton variant="compact" label="Cargando historial…" />;
    if (history.isError) return <div role="alert" className="flex items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</span><TableActionButton onClick={() => history.refetch()}>Reintentar</TableActionButton></div>;
    const entries = presentMovimientoHistoryItems(history.data ?? []);
    if (!expandedItem || !entries.length) return <p className="text-sm text-slate-500">No hay cambios registrados.</p>;
    const pages = Math.ceil(entries.length / HISTORY_PER_PAGE);
    const visible = entries.slice((historyPage - 1) * HISTORY_PER_PAGE, historyPage * HISTORY_PER_PAGE);
    return <div>
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Historial de cambios</h3>
      <ul className="space-y-2">{visible.map((entry) => {
        const presentation = formatMovimientoHistoryEntry(entry, expandedItem);
        return <li key={entry.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
          <span className="block font-medium text-slate-800">{presentation.title}</span>
          <span className="mt-1 block text-slate-600">{presentation.description}</span>
          <span className="mt-1 block text-xs text-slate-500">{formatFechaHora(entry.fecha_cambio)} · {entry.usuario_nombre || "Usuario no informado"}</span>
        </li>;
      })}</ul>
      {pages > 1 && <nav aria-label="Paginación del historial" className="mt-3 flex gap-2"><TableActionButton disabled={historyPage === 1} onClick={() => setHistoryPage((value) => value - 1)}>Anterior</TableActionButton><span className="self-center text-xs text-slate-500">Página {historyPage} de {pages}</span><TableActionButton disabled={historyPage === pages} onClick={() => setHistoryPage((value) => value + 1)}>Siguiente</TableActionButton></nav>}
    </div>;
  };

  const columns: TableColumn<Erogacion>[] = [
    { id: "numero", header: "Movimiento", sortable: true, render: (item) => <span className="font-medium text-slate-900">{item.numero_movimiento}</span> },
    { id: "fecha", header: "Fecha", sortable: true, render: (item) => formatFecha(item.fecha) },
    { id: "tipo", header: "Tipo", render: (item) => <span className={item.tipo_movimiento === "INGRESO" ? "font-medium text-emerald-700" : "font-medium text-rose-700"}>{item.tipo_movimiento === "INGRESO" ? "Ingreso" : "Egreso"}</span> },
    { id: "fuente", header: "Fuente", render: (item) => item.fuente?.nombre ?? "—" },
    { id: "monto", header: "Monto", sortable: true, align: "right", render: (item) => <span className="whitespace-nowrap font-medium">{formatMovimientoMoney(item.monto, item.moneda)}</span> },
    { id: "estado", header: "Estado", priority: "tertiary", render: (item) => <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${item.deleted_at ? "text-rose-700" : "text-emerald-700"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${item.deleted_at ? "bg-rose-500" : "bg-emerald-500"}`} />{item.deleted_at ? "Inactivo" : "Activo"}</span> },
    { id: "acciones", header: "Acciones", align: "right", render: (item) => <TableActions>
      <TableRowActionButton action="view" aria-label={`Ver detalle de ${movementLabel(item)}`} onClick={() => navigate(`/movimientos/${item.id}`, { state: buildMemoriaDetailState(location) })} />
      {!item.deleted_at && canEditRecords() && <TableRowActionButton action="edit" aria-label={`Editar ${movementLabel(item)}`} onClick={() => navigate(`/movimientos/${item.id}/editar`)} />}
      {!item.deleted_at && canDeleteRecords() && <TableRowActionButton action="delete" aria-label={`Eliminar ${movementLabel(item)}`} onClick={() => setPendingDelete(item)} />}
    </TableActions> },
  ];

  return <>
    <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div><h2 className="text-2xl font-semibold md:text-3xl">Movimientos financieros</h2><p className="mt-1 text-sm text-slate-500">Saldo disponible e historial de ingresos y egresos del grupo.</p></div>
        {canCreateRecords() && <Button size="sm" onClick={() => navigate("/movimientos/nuevo")}>Agregar nuevo</Button>}
      </div>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Resumen financiero">
        <article className="rounded-2xl border border-slate-800 bg-slate-800 p-5 text-white shadow-sm sm:col-span-2 lg:col-span-1">
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-200">Saldo disponible</h3>
          <p className="mt-2 text-2xl font-semibold" aria-live="polite">{resumen.data ? formatMovimientoMoney(resumen.data.saldo_disponible) : "—"}</p>
          <p className="mt-1 text-xs text-slate-300">Ingresos menos egresos activos</p>
        </article>
        {(["total_ingresos", "total_egresos", "cantidad_movimientos"] as const).map((key) => <article key={key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">{key === "total_ingresos" ? "Total de ingresos" : key === "total_egresos" ? "Total de egresos" : "Movimientos activos"}</h3>
          <p className="mt-2 text-xl font-semibold text-slate-900">{resumen.data ? key === "cantidad_movimientos" ? resumen.data[key] : formatMovimientoMoney(resumen.data[key]) : "—"}</p>
        </article>)}
      </div>
      {resumen.isLoading && <LoadingSkeleton variant="compact" label="Cargando saldo disponible…" />}
      {resumen.isError && <div role="alert" className="mb-4 flex items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar el saldo. Intente nuevamente.</span><TableActionButton onClick={() => resumen.refetch()}>Reintentar</TableActionButton></div>}
      <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="saldos-por-fuente-title">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 id="saldos-por-fuente-title" className="text-lg font-semibold text-slate-900">Saldo por fuente de financiamiento</h3>
          <TableFilterSelect
            label="Filtrar dashboard por fuente de financiamiento"
            placeholder="Todas las fuentes"
            value={fuenteDashboardActual}
            onValueChange={(value) => { setFuenteDashboard(value); setFuentesPage(1); }}
            options={fuentesDashboard.map((item) => ({ value: String(item.fuente_id), label: item.fuente_nombre }))}
            disabled={fuentesDashboard.length === 0}
            className="max-w-full sm:max-w-64"
          />
        </div>
        <p className="mt-1 text-sm text-slate-500">Ingresos menos egresos activos imputados a cada fuente.</p>
        {saldosPorFuente.isLoading && <LoadingSkeleton variant="compact" label="Cargando saldos por fuente…" />}
        {saldosPorFuente.isError && <div role="alert" className="mt-4 flex items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar los saldos por fuente. Intente nuevamente.</span><TableActionButton onClick={() => saldosPorFuente.refetch()}>Reintentar</TableActionButton></div>}
        {saldosPorFuente.isSuccess && saldosPorFuente.data.length === 0 && <p className="mt-4 text-sm text-slate-500">Aún no hay movimientos registrados para este grupo.</p>}
        {saldosPorFuente.isSuccess && saldosPorFuente.data.length > 0 && <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {fuentesPaginadas.map((item) => <article key={item.fuente_id} className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h4 className="truncate text-sm font-medium text-slate-600" title={item.fuente_nombre}>{item.fuente_nombre}</h4>
            <p className="mt-2 break-words text-xl font-semibold text-slate-900">{formatMovimientoMoney(item.saldo_disponible)}</p>
            <p className="mt-2 text-xs text-slate-600">Ingresos: {formatMovimientoMoney(item.total_ingresos)}</p>
            <p className="mt-1 text-xs text-slate-600">Egresos: {formatMovimientoMoney(item.total_egresos)}</p>
          </article>)}
        </div>}
        {saldosPorFuente.isSuccess && fuentesTotalPages > 1 && <nav aria-label="Paginación de fuentes de financiamiento" className="mt-4 flex items-center justify-center gap-3">
          <TableActionButton disabled={fuentesCurrentPage === 1} onClick={() => setFuentesPage(fuentesCurrentPage - 1)}>Anterior</TableActionButton>
          <span className="text-xs text-slate-500">Página {fuentesCurrentPage} de {fuentesTotalPages}</span>
          <TableActionButton disabled={fuentesCurrentPage === fuentesTotalPages} onClick={() => setFuentesPage(fuentesCurrentPage + 1)}>Siguiente</TableActionButton>
        </nav>}
      </section>
      {memoriaFilter && <div className="mb-4"><MemoriaFilterBanner filter={memoriaFilter} /></div>}
      {movimientos.isError && movimientos.list.length > 0 && <div role="alert" className="mb-4 flex items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos actualizar los movimientos. Intente nuevamente.</span><TableActionButton onClick={() => movimientos.refetch()}>Reintentar</TableActionButton></div>}
      <Table caption="Historial de movimientos financieros" columns={columns} rows={paginated} getRowId={(item) => item.id}
        density="compact" loading={uctLoading || movimientos.isLoading} refreshing={movimientos.isFetching && !movimientos.isLoading}
        error={uctError || (movimientos.isError && movimientos.list.length === 0)}
        onRetry={() => uctError ? queryClient.invalidateQueries({ queryKey: ["uct"] }) : movimientos.refetch()}
        emptyMessage="No hay movimientos que coincidan con los filtros."
        onRowClick={(item) => navigate(`/movimientos/${item.id}`, { state: buildMemoriaDetailState(location) })}
        getRowTitle={(item) => `Ver detalle de ${movementLabel(item)}`}
        expandedRowId={expandedRow} renderExpanded={renderHistory}
        onToggleRow={(item) => { setExpandedRow((current) => current === item.id ? null : item.id); setHistoryPage(1); }}
        getExpandLabel={(item, expanded) => `${expanded ? "Ocultar" : "Mostrar"} historial de ${movementLabel(item)}`}
        sortKey={sortKey} sortDirection={sortDirection}
        onSortChange={(key, direction) => { setSortKey(key); setSortDirection(direction); setPage(1); setExpandedRow(null); }}
        page={page} totalPages={totalPages} totalRecords={filteredList.length}
        onPageChange={(nextPage) => { setPage(nextPage); setExpandedRow(null); }}
        toolbar={<TableToolbar><div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center">
          <TableSearch label="Buscar movimientos" placeholder="Buscar por número, fuente o categoría" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
          <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent" aria-label="Filtros de movimientos">
            <span className="shrink-0 text-xs font-medium text-slate-500">Estado</span>
            <TableFilterChip className="shrink-0" active={!filters.estado} onClick={() => setFilter("estado", "")}>Activos</TableFilterChip>
            <TableFilterChip className="shrink-0" active={filters.estado === "todos"} onClick={() => setFilter("estado", "todos")}>Todos</TableFilterChip>
            <TableFilterChip className="shrink-0" active={filters.estado === "inactivos"} onClick={() => setFilter("estado", "inactivos")}>Inactivos</TableFilterChip>
            <TableFilterSelect label="Filtrar por tipo" placeholder="Todos los tipos" value={filters.tipo || undefined} onValueChange={(value) => setFilter("tipo", value)} options={[{ value: "INGRESO", label: "Ingreso" }, { value: "EGRESO", label: "Egreso" }]} />
            <TableFilterSelect label="Filtrar por fuente" placeholder="Todas las fuentes" value={filters.fuente || undefined} onValueChange={(value) => setFilter("fuente", value)} options={fuentes.map((fuente) => ({ value: String(fuente.id), label: fuente.nombre }))} />
            <TableFilterSelect label="Filtrar por categoría" placeholder="Todas las categorías" value={filters.categoria || undefined} onValueChange={(value) => setFilter("categoria", value)} options={categorias.map((categoria) => ({ value: String(categoria.id), label: categoria.nombre }))} />
            <TableFilterSelect label="Filtrar por año" placeholder="Todos los años" value={filters.anio || undefined} onValueChange={(value) => setFilter("anio", value)} options={years.map((year) => ({ value: String(year), label: String(year) }))} />
            <label className="flex shrink-0 items-center gap-2 text-xs text-slate-600">Desde<input type="date" aria-label="Filtrar desde la fecha" className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs text-slate-700 focus-visible:ring-2 focus-visible:ring-slate-500" value={filters.desde} max={filters.hasta || undefined} onChange={(event) => setFilter("desde", event.target.value)} /></label>
            <label className="flex shrink-0 items-center gap-2 text-xs text-slate-600">Hasta<input type="date" aria-label="Filtrar hasta la fecha" className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs text-slate-700 focus-visible:ring-2 focus-visible:ring-slate-500" value={filters.hasta} min={filters.desde || undefined} onChange={(event) => setFilter("hasta", event.target.value)} /></label>
          </div>
        </div></TableToolbar>}
      />
      <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar movimiento" message={`¿Está seguro de eliminar ${pendingDelete ? movementLabel(pendingDelete) : "este movimiento"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando..." />
    </section>
    <SuccessToast open={Boolean(successMessage)} message={successMessage} onClose={() => setSuccessMessage("")} />
    <SuccessToast open={Boolean(errorMessage)} message={errorMessage} onClose={() => setErrorMessage("")} variant="error" />
  </>;
}
