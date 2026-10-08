import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import MemoriaFilterBanner from "@/components/MemoriaFilterBanner";
import SuccessToast from "@/components/SuccessToast";
import Table, { TableActionButton, TableActions, TableFilterChip, TableRowActionButton, TableSearch, TableToolbar } from "@/components/Table";
import type { TableColumn } from "@/components/Table";
import TableFilterSelect from "@/components/TableFilterSelect";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import { applyMemoriaSectionFilter, getMemoriaSectionFilter } from "@/lib/memoriaSectionFilter";
import { buildMemoriaDetailState } from "@/lib/memoriaNavigation";
import { useEquipamiento } from "@/modules/recursos/hooks/useEquipamiento";
import { getHistorialEquipamientoById, type Equipamiento, type HistorialEquipamientoItem } from "@/modules/recursos/services/equipamientoServices";
import { getCivilYear } from "@/utils/dateTime";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;
const historyLabels: Record<string, string> = {
  denominacion: "Denominación",
  descripcion_breve: "Descripción breve",
  monto_invertido: "Monto invertido",
  fecha_incorporacion: "Fecha de incorporación",
  grupo_utn_id: "Grupo UTN",
};

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value;
};
const formatMoney = (value: number) => Number.isFinite(value)
  ? new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(value)
  : "-";
const formatHistoryValue = (field: string, value: unknown, item: Equipamiento) => {
  if (value === null || value === undefined || value === "") return "-";
  if (field === "monto_invertido") return formatMoney(Number(value));
  if (field === "fecha_incorporacion") return formatDate(String(value));
  if (field === "grupo_utn_id") return Number(value) === item.grupo_utn_id ? item.grupo || "Grupo UTN" : "Grupo UTN";
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean" ? String(value) : "-";
};

export default function EquipamientoLanding() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Equipamiento | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [filters, setFilters] = useState({ estado: "", montoMin: "", montoMax: "", anio: "" });

  const memoriaFilter = useMemo(() => getMemoriaSectionFilter(location.state, "equipamiento"), [location.state]);
  const filtroActivos: "true" | "false" | "all" = memoriaFilter || filters.estado === "todos"
    ? "all" : filters.estado === "inactivos" ? "false" : "true";
  const equipamiento = useEquipamiento(filtroActivos);
  const scopedList = useMemo(
    () => applyMemoriaSectionFilter(equipamiento.list, memoriaFilter),
    [equipamiento.list, memoriaFilter]
  );
  const years = useMemo(() => [...new Set(scopedList.map((item) => getCivilYear(item.fecha_incorporacion))
    .filter((year): year is number => year !== null))].sort((a, b) => b - a)
    .map((year) => ({ value: String(year), label: String(year) })), [scopedList]);
  const filteredList = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase("es");
    return scopedList.filter((item) => {
      const matchesSearch = !query || [item.denominacion, item.descripcion_breve]
        .some((value) => value.toLocaleLowerCase("es").includes(query));
      const matchesMin = !filters.montoMin || item.monto_invertido >= Number(filters.montoMin);
      const matchesMax = !filters.montoMax || item.monto_invertido <= Number(filters.montoMax);
      const matchesYear = !filters.anio || getCivilYear(item.fecha_incorporacion) === Number(filters.anio);
      return matchesSearch && matchesMin && matchesMax && matchesYear;
    });
  }, [scopedList, searchQuery, filters]);
  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const paginatedItems = useMemo(() => filteredList.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE), [filteredList, page]);
  const expandedItem = expandedRow === null ? undefined : scopedList.find((item) => item.id === expandedRow);
  const history = useQuery({
    queryKey: ["equipamiento-historial", expandedItem?.id],
    queryFn: () => getHistorialEquipamientoById(expandedItem!.id),
    enabled: Boolean(expandedItem),
    staleTime: 5 * 60_000,
  });

  useEffect(() => { setPage(1); setExpandedRow(null); }, [filters, searchQuery]);
  useEffect(() => { if (page > Math.max(totalPages, 1)) setPage(Math.max(totalPages, 1)); }, [page, totalPages]);
  useEffect(() => {
    if (!location.state?.successMessage) return;
    setSuccessMessage(location.state.successMessage);
    setShowSuccess(true);
    navigate(location.pathname, { replace: true });
  }, [location.pathname, location.state, navigate]);

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || !canDeleteRecords()) return;
    try {
      await equipamiento.remove(pendingDelete.id);
      await queryClient.invalidateQueries({ queryKey: ["equipamiento"] });
      setPendingDelete(null);
      setSuccessMessage("Equipamiento eliminado con éxito.");
      setShowSuccess(true);
    } catch (error) {
      setPendingDelete(null);
      setErrorMessage(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
      setShowError(true);
    }
  };

  const renderHistory = (item: Equipamiento) => {
    if (history.isLoading) return <LoadingSkeleton variant="compact" label="Cargando historial…" />;
    if (history.isError) return <div role="alert" className="flex items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</span><TableActionButton onClick={() => { void history.refetch(); }}>Reintentar</TableActionButton></div>;
    const entries = (history.data ?? []).filter((entry: HistorialEquipamientoItem) =>
      Boolean(entry.campo && historyLabels[entry.campo]) &&
      entry.valor_anterior !== null && entry.valor_anterior !== undefined && entry.valor_anterior !== "" &&
      formatHistoryValue(entry.campo ?? "", entry.valor_anterior, item) !== formatHistoryValue(entry.campo ?? "", entry.valor_nuevo, item)
    );
    if (!entries.length) return <p className="text-sm text-slate-500">No hay cambios registrados.</p>;
    const pages = Math.ceil(entries.length / HISTORY_PER_PAGE);
    const visible = entries.slice((historyPage - 1) * HISTORY_PER_PAGE, historyPage * HISTORY_PER_PAGE);
    return <div>
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Historial de cambios</h3>
      <ul className="space-y-2">{visible.map((entry) => <li key={entry.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
        <span className="block font-medium text-slate-800">{historyLabels[entry.campo ?? ""]}</span>
        <span className="mt-1 block text-slate-600">{formatHistoryValue(entry.campo ?? "", entry.valor_anterior, item)} → {formatHistoryValue(entry.campo ?? "", entry.valor_nuevo, item)}</span>
        <span className="mt-1 block text-xs text-slate-500">{formatDate(entry.fecha_cambio)}{entry.usuario_nombre ? ` · Por ${entry.usuario_nombre}` : ""}</span>
      </li>)}</ul>
      {pages > 1 && <nav aria-label="Paginación del historial" className="mt-3 flex gap-2"><TableActionButton disabled={historyPage === 1} onClick={() => setHistoryPage((value) => value - 1)}>Anterior</TableActionButton><span className="self-center text-xs text-slate-500">Página {historyPage} de {pages}</span><TableActionButton disabled={historyPage === pages} onClick={() => setHistoryPage((value) => value + 1)}>Siguiente</TableActionButton></nav>}
    </div>;
  };

  const columns: TableColumn<Equipamiento>[] = [
    { id: "denominacion", header: "Equipamiento", render: (item) => <div><span className="block font-medium text-slate-900">{item.denominacion || "-"}</span><span className="mt-0.5 block text-xs text-slate-500">{item.descripcion_breve || "Sin descripción"}</span></div> },
    { id: "fecha", header: "Fecha de incorporación", priority: "secondary", render: (item) => formatDate(item.fecha_incorporacion) },
    { id: "monto", header: "Monto invertido", priority: "tertiary", render: (item) => formatMoney(item.monto_invertido) },
    { id: "estado", header: "Estado", render: (item) => { const active = !item.deleted_at; return <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${active ? "text-emerald-700" : "text-rose-700"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${active ? "bg-emerald-500" : "bg-rose-500"}`} />{active ? "Activo" : "Inactivo"}</span>; } },
    { id: "acciones", header: "Acciones", align: "right", render: (item) => <TableActions>
      <TableRowActionButton action="view" aria-label={`Ver detalle de ${item.denominacion || "equipamiento"}`} onClick={() => navigate(`/equipamiento/${item.id}`, { state: buildMemoriaDetailState(location) })} />
      {!item.deleted_at && canEditRecords() && <TableRowActionButton action="edit" aria-label={`Editar ${item.denominacion || "equipamiento"}`} onClick={() => navigate(`/equipamiento/${item.id}/editar`)} />}
      {!item.deleted_at && canDeleteRecords() && <TableRowActionButton action="delete" aria-label={`Eliminar ${item.denominacion || "equipamiento"}`} onClick={() => setPendingDelete(item)} />}
    </TableActions> },
  ];
  const setFilter = (field: keyof typeof filters, value?: string) => setFilters((current) => ({ ...current, [field]: value ?? "" }));
  const quickEstadoActual = filters.estado === "todos" ? "todos" : filters.estado === "inactivos" ? "inactivos" : "activos";

  return <>
    <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div><h2 className="text-2xl font-semibold md:text-3xl">Equipamiento e Infraestructura</h2><p className="mt-1 text-sm text-slate-500">Consulte el equipamiento, su inversión y estado.</p></div>
        {canCreateRecords() && <Button size="sm" onClick={() => navigate("/equipamiento/nuevo")}>Agregar nuevo</Button>}
      </div>
      {memoriaFilter && <div className="mb-4"><MemoriaFilterBanner filter={memoriaFilter} /></div>}
      <Table
        caption="Listado de equipamiento e infraestructura"
        columns={columns}
        rows={paginatedItems}
        getRowId={(item) => item.id}
        density="compact"
        loading={equipamiento.isLoading}
        refreshing={equipamiento.isFetching && !equipamiento.isLoading}
        error={equipamiento.isError}
        onRetry={() => { void equipamiento.refetch(); }}
        emptyMessage="No hay equipamientos que coincidan con los filtros."
        onRowClick={(item) => navigate(`/equipamiento/${item.id}`, { state: buildMemoriaDetailState(location) })}
        getRowTitle={(item) => `Ver detalle de ${item.denominacion || "equipamiento"}`}
        expandedRowId={expandedRow}
        renderExpanded={renderHistory}
        onToggleRow={(item) => { setExpandedRow((current) => current === item.id ? null : item.id); setHistoryPage(1); }}
        getExpandLabel={(item, expanded) => `${expanded ? "Ocultar" : "Mostrar"} historial de ${item.denominacion || "equipamiento"}`}
        page={page}
        totalPages={totalPages}
        totalRecords={filteredList.length}
        onPageChange={(nextPage) => { setExpandedRow(null); setPage(nextPage); }}
        toolbar={<TableToolbar><div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center">
          <TableSearch label="Buscar equipamiento" placeholder="Buscar por denominación o descripción" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
          <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent" aria-label="Filtros de equipamiento">
            <span className="shrink-0 text-xs font-medium text-slate-500">Estado</span>
            <TableFilterChip className="shrink-0" active={quickEstadoActual === "activos"} onClick={() => setFilter("estado", "")}>Activos</TableFilterChip>
            <TableFilterChip className="shrink-0" active={quickEstadoActual === "todos"} onClick={() => setFilter("estado", "todos")}>Todos</TableFilterChip>
            <TableFilterChip className="shrink-0" active={quickEstadoActual === "inactivos"} onClick={() => setFilter("estado", "inactivos")}>Inactivos</TableFilterChip>
            <TableFilterSelect label="Filtrar por año de incorporación" placeholder="Todos los años" value={filters.anio || undefined} onValueChange={(value) => setFilter("anio", value)} options={years} />
            <label className="flex shrink-0 items-center gap-1 text-xs text-slate-600">Monto desde<input type="number" min="0" step="0.01" className="h-8 w-28 rounded-lg border border-slate-300 bg-white px-2 outline-none focus-visible:ring-2 focus-visible:ring-slate-500" placeholder="Mínimo" value={filters.montoMin} onChange={(event) => setFilter("montoMin", event.target.value)} /></label>
            <label className="flex shrink-0 items-center gap-1 text-xs text-slate-600">Hasta<input type="number" min="0" step="0.01" className="h-8 w-28 rounded-lg border border-slate-300 bg-white px-2 outline-none focus-visible:ring-2 focus-visible:ring-slate-500" placeholder="Máximo" value={filters.montoMax} onChange={(event) => setFilter("montoMax", event.target.value)} /></label>
          </div>
        </div></TableToolbar>}
      />
      <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar equipamiento" message={`¿Está seguro de eliminar ${pendingDelete?.denominacion || "este equipamiento"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando..." />
    </section>
    <SuccessToast open={showSuccess} message={successMessage} onClose={() => setShowSuccess(false)} />
    <SuccessToast open={showError} message={errorMessage} onClose={() => setShowError(false)} variant="error" />
  </>;
}
