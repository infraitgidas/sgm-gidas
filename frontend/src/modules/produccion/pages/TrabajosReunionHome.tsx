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
} from "@/components/Table";
import type { TableColumn } from "@/components/Table";
import TableFilterSelect from "@/components/TableFilterSelect";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import { applyMemoriaSectionFilter, getMemoriaSectionFilter } from "@/lib/memoriaSectionFilter";
import { buildMemoriaDetailState } from "@/lib/memoriaNavigation";
import { useTiposReunion } from "@/modules/produccion/hooks/useTiposReunion";
import { useTrabajosReunion } from "@/modules/produccion/hooks/useTrabajosReunion";
import { autorClave, autorEtiqueta } from "@/modules/produccion/services/trabajoAutoresServices";
import {
  deleteTrabajoReunion,
  getHistorialTrabajoReunionById,
  type HistorialTrabajoReunionItem,
  type TrabajoReunion,
} from "@/modules/produccion/services/trabajosReunionServices";
import {
  formatTrabajoReunionContractValue,
  formatTrabajoReunionHistoryEntry,
  presentTrabajoReunionHistoryItems,
} from "@/modules/produccion/utils/trabajoReunionHistory";
import { getCivilYear } from "@/utils/dateTime";
import { toTitleCase } from "@/utils/format";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;

const formatFecha = (fecha?: string | null) => {
  if (!fecha) return "—";
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(fecha);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : fecha;
};

export default function TrabajosReunionLanding() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();

  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [pendingDelete, setPendingDelete] = useState<TrabajoReunion | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [filters, setFilters] = useState({
    estado: "",
    tipo: "",
    procedencia: "",
    autor: "",
    anio: "",
  });

  const memoriaFilter = useMemo(
    () => getMemoriaSectionFilter(location.state, "trabajos-reunion-cientifica"),
    [location.state]
  );
  const filtroActivos = useMemo<"true" | "false" | "all">(() => {
    if (memoriaFilter || filters.estado === "todos") return "all";
    if (filters.estado === "inactivos") return "false";
    return "true";
  }, [filters.estado, memoriaFilter]);

  const trabajos = useTrabajosReunion(filtroActivos, "asc");
  const { tipos = [] } = useTiposReunion();
  const scopedList = useMemo(
    () => applyMemoriaSectionFilter(trabajos.list, memoriaFilter),
    [trabajos.list, memoriaFilter]
  );

  const filterOptions = useMemo(() => {
    const procedencias = new Set<string>();
    const autores = new Map<string, TrabajoReunion["autores"][number]>();
    const anios = new Set<number>();

    scopedList.forEach((trabajo) => {
      const procedencia = formatTrabajoReunionContractValue(trabajo.procedencia);
      if (procedencia) procedencias.add(toTitleCase(procedencia));
      trabajo.autores.forEach((autor) => autores.set(autorClave(autor), autor));
      const anio = getCivilYear(trabajo.fecha_presentacion);
      if (anio) anios.add(anio);
    });

    return {
      procedencias: Array.from(procedencias).sort((a, b) => a.localeCompare(b, "es")).map((value) => ({ value, label: value })),
      autores: Array.from(autores.values()).sort((a, b) => autorEtiqueta(a).localeCompare(autorEtiqueta(b), "es")).map((autor) => ({ value: autorClave(autor), label: autorEtiqueta(autor) })),
      anios: Array.from(anios).sort((a, b) => b - a).map((value) => ({ value: String(value), label: String(value) })),
    };
  }, [scopedList]);

  const filteredList = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase("es");
    return scopedList.filter((trabajo) => {
      const tipo = formatTrabajoReunionContractValue(trabajo.tipo_reunion);
      const procedencia = formatTrabajoReunionContractValue(trabajo.procedencia);
      const searchable = [trabajo.titulo_trabajo, trabajo.nombre_reunion, procedencia, tipo, ...trabajo.autores.map(autorEtiqueta)];
      const matchesSearch = !query || searchable.some((value) => value.toLocaleLowerCase("es").includes(query));
      const matchesTipo = !filters.tipo || String(trabajo.tipo_reunion?.id ?? "") === filters.tipo;
      const matchesProcedencia = !filters.procedencia || toTitleCase(procedencia) === filters.procedencia;
      const matchesAutor = !filters.autor || trabajo.autores.some((autor) => autorClave(autor) === filters.autor);
      const matchesAnio = !filters.anio || getCivilYear(trabajo.fecha_presentacion) === Number(filters.anio);
      return matchesSearch && matchesTipo && matchesProcedencia && matchesAutor && matchesAnio;
    });
  }, [filters, scopedList, searchQuery]);

  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const paginatedItems = useMemo(() => {
    const start = (page - 1) * ITEMS_PER_PAGE;
    return filteredList.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredList, page]);
  const expandedItem = expandedRow === null ? undefined : scopedList.find((trabajo) => trabajo.id === expandedRow);
  const history = useQuery({
    queryKey: ["trabajo-reunion-historial", expandedItem?.id],
    queryFn: () => getHistorialTrabajoReunionById(expandedItem!.id),
    enabled: Boolean(expandedItem),
    staleTime: 5 * 60_000,
  });
  const tipoNames = useMemo(() => Object.fromEntries(tipos.map((tipo) => [tipo.id, tipo.nombre])), [tipos]);

  useEffect(() => {
    setPage(1);
    setExpandedRow(null);
  }, [filters, searchQuery]);

  useEffect(() => {
    if (page > Math.max(totalPages, 1)) setPage(Math.max(totalPages, 1));
  }, [page, totalPages]);

  useEffect(() => {
    if (!location.state?.successMessage) return;
    setSuccessMessage(location.state.successMessage);
    setShowSuccess(true);
    navigate(location.pathname, { replace: true });
  }, [location.pathname, location.state, navigate]);

  const quickEstadoActual = filters.estado === "todos" ? "todos" : filters.estado === "inactivos" ? "inactivos" : "activos";

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || !canDeleteRecords()) return;
    try {
      await deleteTrabajoReunion(pendingDelete.id);
      await queryClient.invalidateQueries({ queryKey: ["trabajos-reunion"] });
      setPendingDelete(null);
      setSuccessMessage("Trabajo eliminado con éxito.");
      setShowSuccess(true);
    } catch (error) {
      setPendingDelete(null);
      setErrorMessage(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
      setShowError(true);
    }
  };

  const renderHistory = () => {
    if (history.isLoading) return <LoadingSkeleton variant="compact" label="Cargando historial…" />;
    if (history.isError) {
      return <div role="alert" className="flex items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</span><TableActionButton onClick={() => history.refetch()}>Reintentar</TableActionButton></div>;
    }
    const entries = presentTrabajoReunionHistoryItems((history.data ?? []) as HistorialTrabajoReunionItem[]);
    if (!entries.length) return <p className="text-sm text-slate-500">No hay cambios registrados.</p>;
    const pages = Math.ceil(entries.length / HISTORY_PER_PAGE);
    const visible = entries.slice((historyPage - 1) * HISTORY_PER_PAGE, historyPage * HISTORY_PER_PAGE);
    return (
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-900">Historial de cambios</h3>
        <ul className="space-y-2">
          {visible.map((entry) => {
            const presentation = formatTrabajoReunionHistoryEntry(entry, tipoNames);
            return <li key={entry.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm"><span className="block font-medium text-slate-800">{presentation.title}</span><span className="mt-1 block text-slate-600">{presentation.description}</span>{entry.usuario_nombre && <span className="mt-1 block text-xs text-slate-500">Por {entry.usuario_nombre}</span>}</li>;
          })}
        </ul>
        {pages > 1 && <nav aria-label="Paginación del historial" className="mt-3 flex gap-2"><TableActionButton disabled={historyPage === 1} onClick={() => setHistoryPage((value) => value - 1)}>Anterior</TableActionButton><span className="self-center text-xs text-slate-500">Página {historyPage} de {pages}</span><TableActionButton disabled={historyPage === pages} onClick={() => setHistoryPage((value) => value + 1)}>Siguiente</TableActionButton></nav>}
      </div>
    );
  };

  const columns: TableColumn<TrabajoReunion>[] = [
    { id: "titulo", header: "Trabajo", render: (trabajo) => <div><span className="block font-medium text-slate-900">{formatTrabajoReunionContractValue(trabajo.titulo_trabajo) || "—"}</span><span className="mt-0.5 block text-xs text-slate-500">{trabajo.autores.length ? trabajo.autores.map(autorEtiqueta).join(", ") : "Sin autores informados"}</span></div> },
    { id: "reunion", header: "Reunión", priority: "secondary", render: (trabajo) => <div><span className="block text-slate-800">{toTitleCase(formatTrabajoReunionContractValue(trabajo.nombre_reunion)) || "—"}</span><span className="mt-0.5 block text-xs text-slate-500">{toTitleCase(formatTrabajoReunionContractValue(trabajo.procedencia)) || "Sin procedencia"}</span></div> },
    { id: "tipo", header: "Tipo", priority: "tertiary", render: (trabajo) => toTitleCase(formatTrabajoReunionContractValue(trabajo.tipo_reunion)) || "—" },
    { id: "fecha", header: "Fecha de presentación", priority: "tertiary", render: (trabajo) => formatFecha(trabajo.fecha_presentacion) },
    { id: "estado", header: "Estado", render: (trabajo) => { const activo = !trabajo.deleted_at && trabajo.activo !== false; return <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${activo ? "text-emerald-700" : "text-rose-700"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${activo ? "bg-emerald-500" : "bg-rose-500"}`} />{activo ? "Activo" : "Inactivo"}</span>; } },
    { id: "acciones", header: "Acciones", align: "right", render: (trabajo) => { const activo = !trabajo.deleted_at && trabajo.activo !== false; const titulo = formatTrabajoReunionContractValue(trabajo.titulo_trabajo) || "trabajo"; return <TableActions><TableRowActionButton action="view" aria-label={`Ver detalle de ${titulo}`} onClick={() => navigate(`/trabajos-reunion/${trabajo.id}`, { state: buildMemoriaDetailState(location) })} />{activo && canEditRecords() && <TableRowActionButton action="edit" aria-label={`Editar ${titulo}`} onClick={() => navigate(`/trabajos-reunion/${trabajo.id}/editar`)} />}{activo && canDeleteRecords() && <TableRowActionButton action="delete" aria-label={`Eliminar ${titulo}`} onClick={() => setPendingDelete(trabajo)} />}</TableActions>; } },
  ];

  const setFilter = (field: keyof typeof filters, value?: string) => setFilters((current) => ({ ...current, [field]: value ?? "" }));

  return (
    <>
      <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div><h2 className="text-2xl font-semibold md:text-3xl">Trabajos presentados en Congresos</h2><p className="mt-1 text-sm text-slate-500">Gestione los trabajos, sus reuniones, autores y estados.</p></div>
          {canCreateRecords() && <Button size="sm" onClick={() => navigate("/trabajos-reunion/nuevo")}>Agregar nuevo</Button>}
        </div>
        {memoriaFilter && <div className="mb-4"><MemoriaFilterBanner filter={memoriaFilter} /></div>}

        <Table
          caption="Listado de trabajos presentados en congresos"
          columns={columns}
          rows={paginatedItems}
          getRowId={(trabajo) => trabajo.id}
          density="compact"
          loading={trabajos.isLoading}
          refreshing={trabajos.isFetching && !trabajos.isLoading}
          error={trabajos.isError}
          onRetry={() => trabajos.refetch()}
          emptyMessage="No hay trabajos en reuniones que coincidan con los filtros."
          onRowClick={(trabajo) => navigate(`/trabajos-reunion/${trabajo.id}`, { state: buildMemoriaDetailState(location) })}
          getRowTitle={(trabajo) => `Ver detalle de ${formatTrabajoReunionContractValue(trabajo.titulo_trabajo) || "trabajo"}`}
          expandedRowId={expandedRow}
          renderExpanded={renderHistory}
          onToggleRow={(trabajo) => { setExpandedRow((current) => current === trabajo.id ? null : trabajo.id); setHistoryPage(1); }}
          getExpandLabel={(trabajo, expanded) => `${expanded ? "Ocultar" : "Mostrar"} historial de ${formatTrabajoReunionContractValue(trabajo.titulo_trabajo) || "trabajo"}`}
          page={page}
          totalPages={totalPages}
          totalRecords={filteredList.length}
          onPageChange={(nextPage) => { setExpandedRow(null); setPage(nextPage); }}
          toolbar={<TableToolbar><div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center"><TableSearch label="Buscar trabajos en reuniones" placeholder="Buscar por trabajo, reunión o autor" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} /><div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent" aria-label="Filtros de trabajos en reuniones"><span className="shrink-0 text-xs font-medium text-slate-500">Estado</span><TableFilterChip className="shrink-0" active={quickEstadoActual === "activos"} onClick={() => setFilter("estado", "")}>Activos</TableFilterChip><TableFilterChip className="shrink-0" active={quickEstadoActual === "todos"} onClick={() => setFilter("estado", "todos")}>Todos</TableFilterChip><TableFilterChip className="shrink-0" active={quickEstadoActual === "inactivos"} onClick={() => setFilter("estado", "inactivos")}>Inactivos</TableFilterChip><TableFilterSelect label="Filtrar por tipo de reunión" placeholder="Todos los tipos" value={filters.tipo || undefined} onValueChange={(value) => setFilter("tipo", value)} options={tipos.map((tipo) => ({ value: String(tipo.id), label: toTitleCase(tipo.nombre) }))} /><TableFilterSelect label="Filtrar por procedencia" placeholder="Todas las procedencias" value={filters.procedencia || undefined} onValueChange={(value) => setFilter("procedencia", value)} options={filterOptions.procedencias} /><TableFilterSelect label="Filtrar por autor" placeholder="Todos los autores" value={filters.autor || undefined} onValueChange={(value) => setFilter("autor", value)} options={filterOptions.autores} /><TableFilterSelect label="Filtrar por año" placeholder="Todos los años" value={filters.anio || undefined} onValueChange={(value) => setFilter("anio", value)} options={filterOptions.anios} /></div></div></TableToolbar>}
        />

        <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar trabajo en reunión" message={`¿Está seguro de eliminar ${formatTrabajoReunionContractValue(pendingDelete?.titulo_trabajo) || "este trabajo"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando..." />
      </section>
      <SuccessToast open={showSuccess} message={successMessage} onClose={() => setShowSuccess(false)} />
      <SuccessToast open={showError} message={errorMessage} onClose={() => setShowError(false)} variant="error" />
    </>
  );
}
