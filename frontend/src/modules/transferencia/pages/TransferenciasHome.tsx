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
import { getMemoriaSectionFilter } from "@/lib/memoriaSectionFilter";
import { buildMemoriaDetailState, stripSuccessMessageState } from "@/lib/memoriaNavigation";
import { deleteTransferencia, getTransferenciasPage, getHistorialTransferenciaById, type Transferencia } from "@/modules/transferencia/services/transferenciasServices";
import { formatFechaHora } from "@/utils/dateTime";
import { formatTransferenciaHistory, presentTransferenciaHistory } from "@/modules/transferencia/utils/transferenciaHistory";

const HISTORY_SIZE = 3;
const isActive = (item: Transferencia) => item.activo && !item.deletedAt;

export default function TransferenciasHome() {
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ estado: "", tipo: "", grupo: "", anio: "" });
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [direction, setDirection] = useState<"asc" | "desc">("asc");
  const [pendingDelete, setPendingDelete] = useState<Transferencia | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const memoriaFilter = useMemo(() => getMemoriaSectionFilter(location.state, "transferencias"), [location.state]);
  const estado: "true" | "false" | "all" = memoriaFilter || filters.estado === "todos" ? "all" : filters.estado === "inactivos" ? "false" : "true";
  const params = { page, activos: estado, q: search, direction, filters, ids: memoriaFilter?.ids };
  const result = useQuery({
    queryKey: ["transferencias", "table", params],
    queryFn: () => getTransferenciasPage(params),
    staleTime: 60_000,
  });
  const query = { ...result, list: result.data?.data ?? [] };
  const scoped = query.list;
  const facet = (key: string) => result.data?.meta.options[key] ?? [];
  const options = { tipos: facet("tipo"), grupos: facet("grupo"),
    anios: [...facet("anio")].sort((a, b) => Number(b.value) - Number(a.value)) };
  const totalPages = result.data?.meta.total_pages ?? 0;
  const rows = query.list;
  const expandedItem = scoped.find(item => item.id === expanded);
  const history = useQuery({ queryKey: ["transferencia-historial", expandedItem?.id], queryFn: () => getHistorialTransferenciaById(expandedItem!.id), enabled: Boolean(expandedItem) });
  useEffect(() => { setPage(1); setExpanded(null); }, [search, filters, direction, memoriaFilter]);
  useEffect(() => {
    if (result.data && page > Math.max(1, totalPages)) setPage(Math.max(1, totalPages));
  }, [page, totalPages, result.data]);
  useEffect(() => { if (location.state?.successMessage) { setSuccess(location.state.successMessage); navigate(location.pathname, { replace: true, state: stripSuccessMessageState(location.state) }); } }, [location.pathname, location.state, navigate]);

  const confirmDelete = async () => {
    if (!pendingDelete || !isActive(pendingDelete) || !canDeleteRecords()) return;
    try {
      await deleteTransferencia(pendingDelete.id);
      await qc.invalidateQueries({ queryKey: ["transferencias"] });
      setPendingDelete(null);
      setSuccess("Transferencia eliminada con éxito.");
    } catch (cause) {
      setPendingDelete(null);
      setError(getErrorMessage(cause, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
    }
  };
  const columns: TableColumn<Transferencia>[] = [
    { id: "numero", header: "Número", render: item => `#${item.numeroTransferencia}` },
    { id: "denominacion", header: "Transferencia", sortable: true, render: item => <div><span className="block font-medium text-slate-900">{item.denominacion || "—"}</span><span className="text-xs text-slate-500">{item.demandante || "—"}</span></div> },
    { id: "tipo", header: "Tipo de contrato", priority: "secondary", render: item => item.tipoContrato || "—" },
    { id: "grupo", header: "Grupo UTN", priority: "tertiary", render: item => item.grupo || "—" },
    { id: "estado", header: "Estado", render: item => <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${isActive(item) ? "text-emerald-700" : "text-rose-700"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${isActive(item) ? "bg-emerald-500" : "bg-rose-500"}`} />{isActive(item) ? "Activo" : "Inactivo"}</span> },
    { id: "acciones", header: "Acciones", align: "right", render: item => <TableActions><TableRowActionButton action="view" aria-label={`Ver transferencia ${item.numeroTransferencia}`} onClick={() => navigate(`/transferencias/${item.id}`, { state: buildMemoriaDetailState(location) })} />{isActive(item) && canEditRecords() && <TableRowActionButton action="edit" aria-label={`Editar transferencia ${item.numeroTransferencia}`} onClick={() => navigate(`/transferencias/${item.id}/editar`)} />}{isActive(item) && canDeleteRecords() && <TableRowActionButton action="delete" aria-label={`Eliminar transferencia ${item.numeroTransferencia}`} onClick={() => setPendingDelete(item)} />}</TableActions> },
  ];
  const renderHistory = () => {
    if (history.isLoading) return <LoadingSkeleton variant="compact" label="Cargando historial…" />;
    if (history.isError) return <p role="alert" className="text-sm text-rose-700">Lo sentimos, no pudimos recuperar el historial. <TableActionButton onClick={() => history.refetch()}>Reintentar</TableActionButton></p>;
    const items = presentTransferenciaHistory(history.data ?? []);
    if (!items.length) return <p className="text-sm text-slate-500">No hay cambios registrados.</p>;
    const pages = Math.ceil(items.length / HISTORY_SIZE);
    return <div><h3 className="mb-3 text-sm font-semibold">Historial de cambios</h3><ul className="space-y-2">{items.slice((historyPage - 1) * HISTORY_SIZE, historyPage * HISTORY_SIZE).map(item => { const presentation = formatTransferenciaHistory(item); return <li key={item.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm"><span className="font-medium">{presentation.title}</span><span className="block text-slate-600">{presentation.description}</span><span className="block text-xs text-slate-500">{formatFechaHora(item.fecha_cambio)} · {item.usuario_nombre || "Usuario no informado"}</span></li>; })}</ul>{pages > 1 && <nav aria-label="Paginación del historial" className="mt-3 flex items-center gap-2"><TableActionButton disabled={historyPage === 1} onClick={() => setHistoryPage(value => value - 1)}>Anterior</TableActionButton><span>Página {historyPage} de {pages}</span><TableActionButton disabled={historyPage === pages} onClick={() => setHistoryPage(value => value + 1)}>Siguiente</TableActionButton></nav>}</div>;
  };
  const setFilter = (key: keyof typeof filters, value?: string) => setFilters(current => ({ ...current, [key]: value ?? "" }));
  return <>
    <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><h2 className="text-2xl font-semibold md:text-3xl">Vinculación socio-productiva</h2><p className="mt-1 text-sm text-slate-500">Gestione transferencias, adoptantes y estados.</p></div>{canCreateRecords() && <Button size="sm" onClick={() => navigate("/transferencias/nuevo")}>Agregar nuevo</Button>}</div>
      {memoriaFilter && <div className="mb-4"><MemoriaFilterBanner filter={memoriaFilter} /></div>}
      {query.isError && query.list.length > 0 && <p role="alert" className="mb-3 text-sm text-rose-700">Lo sentimos, no pudimos actualizar la información. <button type="button" className="underline" onClick={() => query.refetch()}>Reintentar</button></p>}
      <Table caption="Listado de transferencias" columns={columns} rows={rows} getRowId={item => item.id} density="compact" loading={query.isLoading} refreshing={query.isFetching && !query.isLoading} error={query.isError && query.list.length === 0} onRetry={query.refetch} emptyMessage="No hay transferencias que coincidan con los filtros." onRowClick={item => navigate(`/transferencias/${item.id}`, { state: buildMemoriaDetailState(location) })} getRowTitle={item => `Ver transferencia ${item.numeroTransferencia}`} sortKey="denominacion" sortDirection={direction} onSortChange={(_, next) => setDirection(next)} expandedRowId={expanded} renderExpanded={renderHistory} onToggleRow={item => { setExpanded(value => value === item.id ? null : item.id); setHistoryPage(1); }} getExpandLabel={(item, open) => `${open ? "Ocultar" : "Mostrar"} historial de transferencia ${item.numeroTransferencia}`} page={page} totalPages={totalPages} totalRecords={result.data?.meta.total ?? 0} onPageChange={value => { setPage(value); setExpanded(null); }} toolbar={<TableToolbar><div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center"><TableSearch label="Buscar transferencias" placeholder="Buscar por número, transferencia o adoptante" value={search} onChange={event => setSearch(event.target.value)} /><div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent" aria-label="Filtros de transferencias"><span className="shrink-0 text-xs font-medium text-slate-500">Estado</span><TableFilterChip className="shrink-0" active={!filters.estado} onClick={() => setFilter("estado", "")}>Activas</TableFilterChip><TableFilterChip className="shrink-0" active={filters.estado === "todos"} onClick={() => setFilter("estado", "todos")}>Todas</TableFilterChip><TableFilterChip className="shrink-0" active={filters.estado === "inactivos"} onClick={() => setFilter("estado", "inactivos")}>Inactivas</TableFilterChip><TableFilterSelect label="Filtrar por tipo de contrato" placeholder="Todos los tipos" value={filters.tipo || undefined} onValueChange={value => setFilter("tipo", value)} options={options.tipos} /><TableFilterSelect label="Filtrar por grupo" placeholder="Todos los grupos" value={filters.grupo || undefined} onValueChange={value => setFilter("grupo", value)} options={options.grupos} /><TableFilterSelect label="Filtrar por año" placeholder="Todos los años" value={filters.anio || undefined} onValueChange={value => setFilter("anio", value)} options={options.anios} /></div></div></TableToolbar>} />
      <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar transferencia" message={`¿Está seguro de eliminar ${pendingDelete?.denominacion || "esta transferencia"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando..." />
    </section>
    <SuccessToast open={Boolean(success)} message={success} onClose={() => setSuccess("")} />
    <SuccessToast open={Boolean(error)} message={error} onClose={() => setError("")} variant="error" />
  </>;
}
