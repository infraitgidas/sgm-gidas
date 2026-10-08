import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import MemoriaFilterBanner from "@/components/MemoriaFilterBanner";
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
import { applyMemoriaSectionFilter, getMemoriaSectionFilter } from "@/lib/memoriaSectionFilter";
import { buildMemoriaDetailState } from "@/lib/memoriaNavigation";
import { useParticipaciones } from "@/modules/proyectos/hooks/useParticipaciones";
import {
  getHistorialParticipacionById,
  type HistorialParticipacionItem,
  type Participacion,
} from "@/modules/proyectos/services/participacionesServices";
import {
  formatParticipacionHistoryEntry,
  presentParticipacionHistoryItems,
} from "@/modules/proyectos/utils/participacionHistory";
import { formatFechaHora, getCivilYear } from "@/utils/dateTime";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;
const FORMA_LABELS: Record<string, string> = {
  jurado: "Jurado",
  evaluador: "Evaluador",
  panelista: "Panelista",
  comite: "Miembro de comité científico",
};

const formatDate = (value?: string | null) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value ?? "");
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value || "-";
};

export default function ParticipacionesHome() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({ estado: "", categoria: "", forma: "", anio: "" });
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<Participacion | null>(null);
  const [successMessage, setSuccessMessage] = useState("");
  const [showSuccess, setShowSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [showError, setShowError] = useState(false);

  const memoriaFilter = useMemo(
    () => getMemoriaSectionFilter(location.state, "participaciones-relevantes"),
    [location.state]
  );
  const activos = useMemo<"true" | "false" | "all">(() => {
    if (memoriaFilter || filters.estado === "todos") return "all";
    if (filters.estado === "inactivos") return "false";
    return "true";
  }, [filters.estado, memoriaFilter]);
  const participaciones = useParticipaciones(activos);
  const scopedList = useMemo(
    () => applyMemoriaSectionFilter(participaciones.list, memoriaFilter),
    [memoriaFilter, participaciones.list]
  );
  const options = useMemo(() => {
    const years = new Set<number>();
    const forms = new Set<string>();
    scopedList.forEach((item) => {
      const year = getCivilYear(item.fecha);
      if (year) years.add(year);
      if (item.forma_participacion) forms.add(item.forma_participacion);
    });
    return {
      years: [...years].sort((a, b) => b - a).map((value) => ({ value: String(value), label: String(value) })),
      forms: [...forms].sort().map((value) => ({ value, label: FORMA_LABELS[value] ?? value })),
    };
  }, [scopedList]);
  const filteredList = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase("es");
    return scopedList.filter((item) => {
      const matchesSearch = !query || [
        item.nombre_evento,
        item.participante.nombre_apellido,
        item.participante.tipo,
        FORMA_LABELS[item.forma_participacion] ?? item.forma_participacion,
        item.fecha,
      ].some((value) => String(value ?? "").toLocaleLowerCase("es").includes(query));
      return matchesSearch
        && (!filters.categoria || item.participante.rol === filters.categoria)
        && (!filters.forma || item.forma_participacion === filters.forma)
        && (!filters.anio || getCivilYear(item.fecha) === Number(filters.anio));
    });
  }, [filters, scopedList, searchQuery]);
  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const paginated = useMemo(
    () => filteredList.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE),
    [filteredList, page]
  );
  const expandedItem = expandedRow === null ? undefined : scopedList.find((item) => item.id === expandedRow);
  const history = useQuery({
    queryKey: ["participacion-historial", expandedItem?.id],
    queryFn: () => getHistorialParticipacionById(expandedItem!.id),
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

  const setFilter = (field: keyof typeof filters, value?: string) =>
    setFilters((current) => ({ ...current, [field]: value ?? "" }));
  const stateFilter = filters.estado === "todos" ? "todos" : filters.estado === "inactivos" ? "inactivos" : "activos";

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || !canDeleteRecords()) return;
    try {
      await participaciones.remove(pendingDelete.id);
      await queryClient.invalidateQueries({ queryKey: ["participaciones"] });
      setPendingDelete(null);
      setSuccessMessage("Participación eliminada con éxito.");
      setShowSuccess(true);
    } catch (error) {
      setPendingDelete(null);
      setErrorMessage(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
      setShowError(true);
    }
  };

  const renderHistory = () => {
    if (history.isLoading) return <LoadingSkeleton variant="compact" label="Cargando historial…" />;
    if (history.isError) return <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</span><TableActionButton onClick={() => history.refetch()}>Reintentar</TableActionButton></div>;
    const entries = presentParticipacionHistoryItems((history.data ?? []) as HistorialParticipacionItem[]);
    if (!entries.length) return <p className="text-sm text-slate-500">No hay cambios registrados.</p>;
    const pages = Math.ceil(entries.length / HISTORY_PER_PAGE);
    const visible = entries.slice((historyPage - 1) * HISTORY_PER_PAGE, historyPage * HISTORY_PER_PAGE);
    return (
      <div>
        <ul className="grid gap-2 md:grid-cols-3">
          {visible.map((entry) => {
            const presentation = formatParticipacionHistoryEntry(entry);
            return <li key={entry.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm"><span className="block font-medium text-slate-800">{presentation.title}</span><span className="mt-1 block text-slate-600">{presentation.description}</span><span className="mt-1 block text-xs text-slate-500">{formatFechaHora(entry.fecha_cambio)} · {entry.usuario_nombre || "Usuario no informado"}</span></li>;
          })}
        </ul>
        {pages > 1 && <nav aria-label="Paginación del historial" className="mt-3 flex gap-2"><TableActionButton disabled={historyPage === 1} onClick={() => setHistoryPage((value) => value - 1)}>Anterior</TableActionButton><span className="self-center text-xs text-slate-500">Página {historyPage} de {pages}</span><TableActionButton disabled={historyPage === pages} onClick={() => setHistoryPage((value) => value + 1)}>Siguiente</TableActionButton></nav>}
      </div>
    );
  };

  const columns: TableColumn<Participacion>[] = [
    { id: "evento", header: "Evento", render: (item) => <span className="font-medium text-slate-900">{item.nombre_evento || "-"}</span> },
    { id: "participante", header: "Participante", render: (item) => <span>{item.participante.nombre_apellido || "-"}<span className="block text-xs text-slate-500">{item.participante.tipo}</span></span> },
    { id: "forma", header: "Forma de participación", priority: "secondary", render: (item) => FORMA_LABELS[item.forma_participacion] ?? item.forma_participacion ?? "-" },
    { id: "fecha", header: "Fecha", priority: "tertiary", render: (item) => formatDate(item.fecha) },
    { id: "estado", header: "Estado", render: (item) => { const active = !item.deleted_at; return <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${active ? "text-emerald-700" : "text-rose-700"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${active ? "bg-emerald-500" : "bg-rose-500"}`} />{active ? "Activo" : "Inactivo"}</span>; } },
    { id: "acciones", header: "Acciones", align: "right", render: (item) => { const active = !item.deleted_at; const label = item.nombre_evento || "participación"; return <TableActions><TableRowActionButton action="view" aria-label={`Ver detalle de ${label}`} onClick={() => navigate(`/participaciones/${item.id}`, { state: buildMemoriaDetailState(location) })} />{active && canEditRecords() && <TableRowActionButton action="edit" aria-label={`Editar ${label}`} onClick={() => navigate(`/participaciones/${item.id}/editar`)} />}{active && canDeleteRecords() && <TableRowActionButton action="delete" aria-label={`Eliminar ${label}`} onClick={() => setPendingDelete(item)} />}</TableActions>; } },
  ];

  return (
    <>
      <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><h2 className="text-2xl font-semibold md:text-3xl">Participaciones relevantes</h2><p className="mt-1 text-sm text-slate-500">Gestione participaciones de investigadores y becarios en actividades institucionales.</p></div>{canCreateRecords() && <Button size="sm" onClick={() => navigate("/participaciones/nuevo")}>Agregar nueva</Button>}</div>
        {memoriaFilter && <div className="mb-4"><MemoriaFilterBanner filter={memoriaFilter} /></div>}
        <Table
          caption="Listado de participaciones relevantes"
          columns={columns}
          rows={paginated}
          getRowId={(item) => item.id}
          density="compact"
          loading={participaciones.isLoading}
          refreshing={participaciones.isFetching && !participaciones.isLoading}
          error={participaciones.isError}
          onRetry={() => participaciones.refetch()}
          emptyMessage="No hay participaciones relevantes que coincidan con los filtros."
          onRowClick={(item) => navigate(`/participaciones/${item.id}`, { state: buildMemoriaDetailState(location) })}
          getRowTitle={(item) => `Ver detalle de ${item.nombre_evento || "la participación"}`}
          expandedRowId={expandedRow}
          renderExpanded={renderHistory}
          onToggleRow={(item) => { setExpandedRow((current) => current === item.id ? null : item.id); setHistoryPage(1); }}
          getExpandLabel={(item, expanded) => `${expanded ? "Ocultar" : "Mostrar"} historial de ${item.nombre_evento || "la participación"}`}
          page={page}
          totalPages={totalPages}
          totalRecords={filteredList.length}
          onPageChange={(value) => { setExpandedRow(null); setPage(value); }}
          toolbar={<TableToolbar><div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center"><TableSearch label="Buscar participaciones relevantes" placeholder="Buscar por evento, participante, categoría, forma o fecha" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} /><div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent" aria-label="Filtros de participaciones relevantes"><span className="shrink-0 text-xs font-medium text-slate-500">Estado</span><TableFilterChip className="shrink-0" active={stateFilter === "activos"} onClick={() => setFilter("estado", "")}>Activos</TableFilterChip><TableFilterChip className="shrink-0" active={stateFilter === "todos"} onClick={() => setFilter("estado", "todos")}>Todos</TableFilterChip><TableFilterChip className="shrink-0" active={stateFilter === "inactivos"} onClick={() => setFilter("estado", "inactivos")}>Inactivos</TableFilterChip><TableFilterSelect label="Filtrar por categoría" placeholder="Todas las categorías" value={filters.categoria || undefined} onValueChange={(value) => setFilter("categoria", value)} options={[{ value: "investigador", label: "Investigadores" }, { value: "becario", label: "Becarios" }]} /><TableFilterSelect label="Filtrar por forma" placeholder="Todas las formas" value={filters.forma || undefined} onValueChange={(value) => setFilter("forma", value)} options={options.forms} /><TableFilterSelect label="Filtrar por año" placeholder="Todos los años" value={filters.anio || undefined} onValueChange={(value) => setFilter("anio", value)} options={options.years} /></div></div></TableToolbar>}
        />
        <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar participación relevante" message={`¿Está seguro de eliminar ${pendingDelete?.nombre_evento || "esta participación"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando…" />
      </section>
      <SuccessToast open={showSuccess} message={successMessage} onClose={() => setShowSuccess(false)} />
      <SuccessToast open={showError} message={errorMessage} onClose={() => setShowError(false)} variant="error" />
    </>
  );
}
