import TableFilterSelect from "@/components/TableFilterSelect";
import { useHomeState, useHomeFilterEffect } from "@/modules/shared/hooks/useHomeState";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import MemoriaFilterBanner from "@/components/MemoriaFilterBanner";
import SuccessToast from "@/components/SuccessToast";
import Table, { TableActionButton, TableActions, TableRowActionButton, TableSearch, TableToolbar } from "@/components/Table";
import type { TableColumn, TableSortDirection } from "@/components/Table";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import { getMemoriaSectionFilter } from "@/lib/memoriaSectionFilter";
import { buildMemoriaDetailState } from "@/lib/memoriaNavigation";
import { usePersonal } from "@/modules/personal/hooks/usePersonal";
import { reactivarPersonal, eliminarPersonal, type PersonalItem, type PersonalSort, type PersonalType } from "@/modules/personal/services/personalServices";
import { getHistorialPersonalByRolAndId } from "@/modules/personal/services/personalCompletoServices";
import { formatPersonalHistoryEntry } from "@/modules/personal/utils/personalHistory";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;

const classLabels: Record<PersonalItem["rol"], string> = {
  personal: "Personal",
  becario: "Becario",
  investigador: "Investigador",
};

export default function PersonalLanding() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const requestedType = searchParams.get("tipo") as PersonalType | null;
  const initialType = requestedType && ["PERSONAL", "BECARIO", "INVESTIGADOR"].includes(requestedType) ? requestedType : "";
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();

  const [page, setPage] = useHomeState("page", 1);
  const [search, setSearch] = useHomeState("search", "");
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  const [classFilter, setClassFilter] = useHomeState<PersonalType | "">("classFilter", initialType, { allowed: ["", "PERSONAL", "BECARIO", "INVESTIGADOR"] });
  const [activeFilter, setActiveFilter] = useHomeState<"true" | "false" | "all">("activeFilter", "true", { allowed: ["true","false","all"] });
  const [sort, setSort] = useHomeState<PersonalSort>("sort", "fecha_alta", { allowed: ["nombre","clase","clasificacion","grupo","horas","estado","fecha_alta"] });
  const [direction, setDirection] = useHomeState<TableSortDirection>("direction", "desc", { allowed: ["asc", "desc"] });
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<PersonalItem | null>(null);
  const [pendingRestore, setPendingRestore] = useState<PersonalItem | null>(null);
  const [motivo, setMotivo] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const memoriaFilter = useMemo(() => getMemoriaSectionFilter(
    location.state,
    classFilter === "INVESTIGADOR" ? "investigadores" : classFilter === "BECARIO" ? "becarios" : "personal",
  ), [location.state, classFilter]);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(search), 250);
    return () => window.clearTimeout(timeout);
  }, [search]);

  useHomeFilterEffect(() => {
    setPage(1);
    setExpandedRow(null);
  }, [debouncedSearch, classFilter, activeFilter, sort, direction, memoriaFilter]);

  useEffect(() => {
    if (location.state?.successMessage) {
      setSuccessMessage(location.state.successMessage);
      navigate(`${location.pathname}${location.search}`, { replace: true, state: { ...location.state, successMessage: undefined } });
    }
  }, [location.pathname, location.search, location.state, navigate]);

  const personal = usePersonal({
    page,
    perPage: ITEMS_PER_PAGE,
    search: debouncedSearch,
    tipo: classFilter || undefined,
    activos: memoriaFilter ? "all" : activeFilter,
    sort,
    direction,
    ids: memoriaFilter?.ids,
  });

  useEffect(() => {
    if (personal.data && !personal.isFetching && !personal.isError && page > Math.max(1, personal.meta.total_pages)) {
      setPage(Math.max(1, personal.meta.total_pages));
    }
  }, [page, personal.data, personal.isFetching, personal.isError, personal.meta.total_pages, setPage]);

  const expandedItem = expandedRow ? personal.list.find((item) => `${item.rol}-${item.id}` === expandedRow) : undefined;
  const history = useQuery({
    queryKey: ["personal-historial", expandedItem?.rol, expandedItem?.id],
    queryFn: () => getHistorialPersonalByRolAndId(expandedItem!.rol, expandedItem!.id),
    enabled: Boolean(expandedItem),
    staleTime: 5 * 60_000,
  });

  const toggleHistory = (item: PersonalItem) => {
    const rowId = `${item.rol}-${item.id}`;
    setExpandedRow((current) => current === rowId ? null : rowId);
    setHistoryPage(1);
  };

  const handleSort = (key: string, nextDirection: TableSortDirection) => {
    setSort(key as PersonalSort);
    setDirection(nextDirection);
  };

  const handlePageChange = (nextPage: number) => {
    setExpandedRow(null);
    setPage(nextPage);
  };

  const confirmDelete = async () => {
    if (!pendingDelete || !canDeleteRecords() || !pendingDelete.activo) return;
    try {
      await eliminarPersonal(pendingDelete.id, pendingDelete.rol, motivo);
      await queryClient.invalidateQueries({ queryKey: ["personal"] });
      await queryClient.invalidateQueries({ queryKey: ["personal-historial"] });
      await queryClient.invalidateQueries({ queryKey: ["personal-detalle"] });
      setPendingDelete(null);
      setSuccessMessage("Registro dado de baja con éxito.");
    } catch (error) {
      setPendingDelete(null);
      setErrorMessage(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
    }
  };

  const columns = useMemo<TableColumn<PersonalItem>[]>(() => [
    { id: "nombre", header: "Nombre y apellido", sortable: true, render: (item) => <span className="font-medium text-slate-900">{item.nombre_apellido}</span> },
    { id: "clase", header: "Clase", sortable: true, render: (item) => classLabels[item.rol] },
    { id: "clasificacion", header: "Clasificación o función", sortable: true, priority: "secondary", render: (item) => item.clasificacion || "—" },
    { id: "grupo", header: "Grupo", sortable: true, priority: "tertiary", render: (item) => item.grupo || "—" },
    { id: "horas", header: "Horas", sortable: true, align: "right", priority: "secondary", render: (item) => `${item.horas_semanales} h` },
    { id: "estado", header: "Estado", sortable: true, render: (item) => <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${item.activo ? "text-emerald-700" : "text-rose-700"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${item.activo ? "bg-emerald-500" : "bg-rose-500"}`} />{item.activo ? "Activo" : "Inactivo"}</span> },
    { id: "acciones", header: "Acciones", align: "right", render: (item) => {
      return <TableActions>
        {!item.activo && canEditRecords() && <TableActionButton onClick={() => setPendingRestore(item)}>Reactivar</TableActionButton>}
        <TableRowActionButton action="view" aria-label={`Ver detalle de ${item.nombre_apellido}`} onClick={() => navigate(`/personal/${item.rol}/${item.id}`, { state: buildMemoriaDetailState(location) })} />
        {item.activo && canEditRecords() && <TableRowActionButton action="edit" aria-label={`Editar ${item.nombre_apellido}`} onClick={() => navigate(`/personal/${item.rol}/${item.id}/editar`)} />}
        {item.activo && canDeleteRecords() && <TableRowActionButton action="delete" label="Dar de baja" aria-label={`Dar de baja a ${item.nombre_apellido}`} onClick={() => { setMotivo(""); setPendingDelete(item); }} />}
      </TableActions>;
    } },
  ], [canDeleteRecords, canEditRecords, location, navigate]);

  const renderHistory = () => {
    if (history.isLoading) return <LoadingSkeleton variant="compact" label="Cargando historial…" />;
    if (history.isError) return <div role="alert" className="flex items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</span><TableActionButton onClick={() => history.refetch()}>Reintentar</TableActionButton></div>;
    const entries = history.data ?? [];
    if (!entries.length) return <p className="text-sm text-slate-500">No hay cambios registrados.</p>;
    const pages = Math.ceil(entries.length / HISTORY_PER_PAGE);
    const visible = entries.slice((historyPage - 1) * HISTORY_PER_PAGE, historyPage * HISTORY_PER_PAGE);
    return <div>
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Historial de cambios</h3>
      <ul className="space-y-2">{visible.map((entry) => {
        const presentation = formatPersonalHistoryEntry(entry);
        return <li key={entry.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm"><span className="block font-medium text-slate-800">{presentation.title}</span><span className="mt-1 block text-slate-600">{presentation.description}</span>{entry.usuario_nombre && <span className="mt-1 block text-xs text-slate-500">Por {entry.usuario_nombre}</span>}</li>;
      })}</ul>
      {pages > 1 && <nav aria-label="Paginación del historial" className="mt-3 flex gap-2"><TableActionButton disabled={historyPage === 1} onClick={() => setHistoryPage((value) => value - 1)}>Anterior</TableActionButton><span className="self-center text-xs text-slate-500">Página {historyPage} de {pages}</span><TableActionButton disabled={historyPage === pages} onClick={() => setHistoryPage((value) => value + 1)}>Siguiente</TableActionButton></nav>}
    </div>;
  };

  const createUrl = classFilter ? `/personal/nuevo?tipo=${classFilter}` : "/personal/nuevo";

  return <section className="w-full min-h-[calc(100vh-120px)] px-4 py-4">
    <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{successMessage}</p>
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div><h2 className="text-2xl font-semibold md:text-3xl">Personal</h2><p className="mt-1 text-sm text-slate-500">Gestione integrantes, permisos y su historial.</p></div>
      {canCreateRecords() && <Button size="sm" onClick={() => navigate(createUrl)}>Agregar nuevo</Button>}
    </div>
    {memoriaFilter && <div className="mb-4"><MemoriaFilterBanner filter={memoriaFilter} /></div>}
    <Table
      caption="Listado de personal"
      columns={columns}
      rows={personal.list}
      getRowId={(item) => `${item.rol}-${item.id}`}
      onRowClick={(item) => navigate(`/personal/${item.rol}/${item.id}`, { state: buildMemoriaDetailState(location) })}
      getRowTitle={(item) => `Ver detalle de ${item.nombre_apellido}`}
      density="compact"
      loading={personal.isLoading}
      refreshing={personal.isFetching && !personal.isLoading}
      error={personal.isError}
      onRetry={() => personal.refetch()}
      emptyMessage="No hay personal que coincida con los filtros."
      sortKey={sort}
      sortDirection={direction}
      onSortChange={handleSort}
      expandedRowId={expandedRow}
      renderExpanded={renderHistory}
      onToggleRow={toggleHistory}
      getExpandLabel={(item, expanded) => `${expanded ? "Ocultar" : "Mostrar"} historial de ${item.nombre_apellido}`}
      page={page}
      totalPages={personal.meta.total_pages}
      totalRecords={personal.meta.total}
      onPageChange={handlePageChange}
      toolbar={
        <TableToolbar>
          <div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center">
            <TableSearch label="Buscar personal" placeholder="Buscar por nombre, clase, función o grupo" value={search} onChange={(event) => setSearch(event.target.value)} />
            <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto pb-1 whitespace-nowrap" aria-label="Filtros de personal">
              <TableFilterSelect
                label="Filtrar por clase de personal"
                placeholder="Todas las clases"
                value={classFilter || undefined}
                onValueChange={(value) => setClassFilter((value ?? "") as typeof classFilter)}
                options={[{ value: "PERSONAL", label: "Personal" }, { value: "BECARIO", label: "Becarios" }, { value: "INVESTIGADOR", label: "Investigadores" }]}
              />

              <TableFilterSelect
                label="Filtrar por estado"
                placeholder="Todos"
                value={activeFilter === "all" ? undefined : activeFilter}
                onValueChange={(value) => setActiveFilter((value ?? "all") as typeof activeFilter)}
                options={[{ value: "true", label: "Activos" }, { value: "false", label: "Inactivos" }]}
              />
            </div>
          </div>
        </TableToolbar>
      }
    />
    <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar personal" message={`¿Está seguro de dar de baja a ${pendingDelete?.nombre_apellido ?? "este registro"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando...">
      <label htmlFor="motivo-baja" className="block text-sm">Motivo de baja (opcional)</label>
      <textarea id="motivo-baja" maxLength={500} value={motivo} onChange={(event) => setMotivo(event.target.value)} placeholder="Ingrese el motivo de la baja" className="mt-2 w-full rounded border border-slate-300 p-2" />
    </ConfirmDialog>
    <ConfirmDialog open={Boolean(pendingRestore)} title="Reactivar personal" message={`Se reactivará a ${pendingRestore?.nombre_apellido ?? "este registro"}, conservando su identidad y relaciones.`} confirmText="Reactivar" onCancel={() => setPendingRestore(null)} onConfirm={async () => {
      if (!pendingRestore || !canEditRecords()) return;
      await reactivarPersonal(pendingRestore.id, pendingRestore.rol);
      await queryClient.invalidateQueries({ queryKey: ["personal"] });
      await queryClient.invalidateQueries({ queryKey: ["personal-historial"] });
      await queryClient.invalidateQueries({ queryKey: ["personal-detalle"] });
      setPendingRestore(null);
      setSuccessMessage("Registro reactivado con éxito.");
    }} />
    <SuccessToast open={Boolean(successMessage)} message={successMessage} onClose={() => setSuccessMessage("")} />
    <SuccessToast open={Boolean(errorMessage)} message={errorMessage} variant="error" onClose={() => setErrorMessage("")} />
  </section>;
}
