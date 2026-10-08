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
import {
  applyMemoriaSectionFilter,
  getMemoriaSectionFilter,
} from "@/lib/memoriaSectionFilter";
import { buildMemoriaDetailState } from "@/lib/memoriaNavigation";
import { useArticulosDivulgacion } from "@/modules/produccion/hooks/useArticulosDivulgacion";
import {
  getHistorialArticuloById,
  type ArticuloDivulgacion,
  type HistorialArticuloDivulgacionItem,
} from "@/modules/produccion/services/articulosDivulgacionServices";
import {
  formatArticuloHistoryEntry,
  presentArticuloHistoryItems,
} from "@/modules/produccion/utils/articuloDivulgacionHistory";
import { formatFechaHora, getCivilYear } from "@/utils/dateTime";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;

const formatDate = (date?: string | null) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date ?? "");
  return match ? `${match[3]}/${match[2]}/${match[1]}` : date || "-";
};

export default function ArticulosDivulgacionHome() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({ estado: "", grupo: "", anio: "" });
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<ArticuloDivulgacion | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const memoriaFilter = useMemo(
    () => getMemoriaSectionFilter(location.state, "articulos-divulgacion"),
    [location.state]
  );
  const activos = useMemo<"true" | "false" | "all">(() => {
    if (memoriaFilter || filters.estado === "todos") return "all";
    if (filters.estado === "inactivos") return "false";
    return "true";
  }, [filters.estado, memoriaFilter]);
  const articulos = useArticulosDivulgacion(activos);
  const scopedList = useMemo(
    () => applyMemoriaSectionFilter(articulos.list, memoriaFilter),
    [articulos.list, memoriaFilter]
  );
  const filterOptions = useMemo(() => {
    const grupos = new Map<number, string>();
    const anios = new Set<number>();
    scopedList.forEach((item) => {
      if (item.grupo_utn?.id && item.grupo_utn.nombre) {
        grupos.set(item.grupo_utn.id, item.grupo_utn.nombre);
      }
      const anio = getCivilYear(item.fecha_publicacion);
      if (anio) anios.add(anio);
    });
    return {
      grupos: [...grupos.entries()]
        .sort((a, b) => a[1].localeCompare(b[1], "es"))
        .map(([value, label]) => ({ value: String(value), label })),
      anios: [...anios]
        .sort((a, b) => b - a)
        .map((value) => ({ value: String(value), label: String(value) })),
    };
  }, [scopedList]);
  const groupNames = useMemo(
    () => Object.fromEntries(filterOptions.grupos.map((option) => [Number(option.value), option.label])),
    [filterOptions.grupos]
  );
  const filteredList = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase("es");
    return scopedList.filter((item) => {
      const matchesSearch =
        !query ||
        [item.titulo, item.descripcion, item.fecha_publicacion, item.grupo_utn?.nombre].some(
          (value) => String(value ?? "").toLocaleLowerCase("es").includes(query)
        );
      const matchesGrupo =
        !filters.grupo || String(item.grupo_utn?.id ?? item.grupo_utn_id) === filters.grupo;
      const matchesAnio =
        !filters.anio || getCivilYear(item.fecha_publicacion) === Number(filters.anio);
      return matchesSearch && matchesGrupo && matchesAnio;
    });
  }, [filters, scopedList, searchQuery]);
  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const paginatedItems = useMemo(() => {
    const start = (page - 1) * ITEMS_PER_PAGE;
    return filteredList.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredList, page]);
  const expandedItem =
    expandedRow === null ? undefined : scopedList.find((item) => item.id === expandedRow);
  const history = useQuery({
    queryKey: ["articulo-divulgacion-historial", expandedItem?.id],
    queryFn: () => getHistorialArticuloById(expandedItem!.id),
    enabled: Boolean(expandedItem),
    staleTime: 5 * 60_000,
  });

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

  const quickEstadoActual =
    filters.estado === "todos"
      ? "todos"
      : filters.estado === "inactivos"
        ? "inactivos"
        : "activos";
  const setFilter = (field: keyof typeof filters, value?: string) =>
    setFilters((current) => ({ ...current, [field]: value ?? "" }));

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || !canDeleteRecords()) return;
    try {
      await articulos.remove(pendingDelete.id);
      await queryClient.invalidateQueries({ queryKey: ["articulos-divulgacion"] });
      setPendingDelete(null);
      setSuccessMessage("Artículo de divulgación eliminado con éxito.");
      setShowSuccess(true);
    } catch (error) {
      setPendingDelete(null);
      setErrorMessage(
        getErrorMessage(
          error,
          "Lo sentimos, no pudimos completar la operación. Intente nuevamente."
        )
      );
      setShowError(true);
    }
  };

  const renderHistory = () => {
    if (history.isLoading) {
      return <LoadingSkeleton variant="compact" label="Cargando historial…" />;
    }
    if (history.isError) {
      return (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-rose-700">
          <span>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</span>
          <TableActionButton onClick={() => history.refetch()}>Reintentar</TableActionButton>
        </div>
      );
    }
    const entries = presentArticuloHistoryItems(
      (history.data ?? []) as HistorialArticuloDivulgacionItem[]
    );
    if (!entries.length) {
      return <p className="text-sm text-slate-500">No hay cambios registrados.</p>;
    }
    const pages = Math.ceil(entries.length / HISTORY_PER_PAGE);
    const visible = entries.slice(
      (historyPage - 1) * HISTORY_PER_PAGE,
      historyPage * HISTORY_PER_PAGE
    );
    return (
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-900">Historial de cambios</h3>
        <ul className="space-y-2">
          {visible.map((entry) => {
            const presentation = formatArticuloHistoryEntry(entry, groupNames);
            return (
              <li key={entry.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
                <span className="block font-medium text-slate-800">{presentation.title}</span>
                <span className="mt-1 block text-slate-600">{presentation.description}</span>
                <span className="mt-1 block text-xs text-slate-500">
                  {formatFechaHora(entry.fecha_cambio)} · {entry.usuario_nombre || "Usuario no informado"}
                </span>
              </li>
            );
          })}
        </ul>
        {pages > 1 && (
          <nav aria-label="Paginación del historial" className="mt-3 flex gap-2">
            <TableActionButton disabled={historyPage === 1} onClick={() => setHistoryPage((value) => value - 1)}>Anterior</TableActionButton>
            <span className="self-center text-xs text-slate-500">Página {historyPage} de {pages}</span>
            <TableActionButton disabled={historyPage === pages} onClick={() => setHistoryPage((value) => value + 1)}>Siguiente</TableActionButton>
          </nav>
        )}
      </div>
    );
  };

  const columns: TableColumn<ArticuloDivulgacion>[] = [
    {
      id: "titulo",
      header: "Título",
      render: (item) => <span className="block font-medium text-slate-900">{item.titulo || "-"}</span>,
    },
    {
      id: "descripcion",
      header: "Descripción",
      priority: "secondary",
      render: (item) => <span className="line-clamp-2 max-w-lg">{item.descripcion || "-"}</span>,
    },
    {
      id: "fecha_publicacion",
      header: "Fecha de publicación",
      priority: "tertiary",
      render: (item) => formatDate(item.fecha_publicacion),
    },
    {
      id: "estado",
      header: "Estado",
      render: (item) => {
        const activo = !item.deleted_at;
        return (
          <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${activo ? "text-emerald-700" : "text-rose-700"}`}>
            <span aria-hidden="true" className={`h-2 w-2 rounded-full ${activo ? "bg-emerald-500" : "bg-rose-500"}`} />
            {activo ? "Activo" : "Inactivo"}
          </span>
        );
      },
    },
    {
      id: "acciones",
      header: "Acciones",
      align: "right",
      render: (item) => {
        const activo = !item.deleted_at;
        const label = item.titulo || "artículo";
        return (
          <TableActions>
            <TableRowActionButton action="view" aria-label={`Ver detalle de ${label}`} onClick={() => navigate(`/articulos-divulgacion/${item.id}`, { state: buildMemoriaDetailState(location) })} />
            {activo && canEditRecords() && (
              <TableRowActionButton action="edit" aria-label={`Editar ${label}`} onClick={() => navigate(`/articulos-divulgacion/${item.id}/editar`)} />
            )}
            {activo && canDeleteRecords() && (
              <TableRowActionButton action="delete" aria-label={`Eliminar ${label}`} onClick={() => setPendingDelete(item)} />
            )}
          </TableActions>
        );
      },
    },
  ];

  return (
    <>
      <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold md:text-3xl">Artículos de divulgación</h2>
            <p className="mt-1 text-sm text-slate-500">Gestione las publicaciones de divulgación, sus fechas y estados.</p>
          </div>
          {canCreateRecords() && <Button size="sm" onClick={() => navigate("/articulos-divulgacion/nuevo")}>Agregar nuevo</Button>}
        </div>

        {memoriaFilter && <div className="mb-4"><MemoriaFilterBanner filter={memoriaFilter} /></div>}

        <Table
          caption="Listado de artículos de divulgación"
          columns={columns}
          rows={paginatedItems}
          getRowId={(item) => item.id}
          density="compact"
          loading={articulos.isLoading}
          refreshing={articulos.isFetching && !articulos.isLoading}
          error={articulos.isError}
          onRetry={() => articulos.refetch()}
          emptyMessage="No hay artículos de divulgación que coincidan con los filtros."
          onRowClick={(item) => navigate(`/articulos-divulgacion/${item.id}`, { state: buildMemoriaDetailState(location) })}
          getRowTitle={(item) => `Ver detalle de ${item.titulo || "artículo"}`}
          expandedRowId={expandedRow}
          renderExpanded={renderHistory}
          onToggleRow={(item) => {
            setExpandedRow((current) => (current === item.id ? null : item.id));
            setHistoryPage(1);
          }}
          getExpandLabel={(item, expanded) => `${expanded ? "Ocultar" : "Mostrar"} historial de ${item.titulo || "el artículo"}`}
          page={page}
          totalPages={totalPages}
          totalRecords={filteredList.length}
          onPageChange={(nextPage) => {
            setExpandedRow(null);
            setPage(nextPage);
          }}
          toolbar={
            <TableToolbar>
              <div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center">
                <TableSearch label="Buscar artículos de divulgación" placeholder="Buscar por título, descripción, UCT o fecha" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
                <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent" aria-label="Filtros de artículos de divulgación">
                  <span className="shrink-0 text-xs font-medium text-slate-500">Estado</span>
                  <TableFilterChip className="shrink-0" active={quickEstadoActual === "activos"} onClick={() => setFilter("estado", "")}>Activos</TableFilterChip>
                  <TableFilterChip className="shrink-0" active={quickEstadoActual === "todos"} onClick={() => setFilter("estado", "todos")}>Todos</TableFilterChip>
                  <TableFilterChip className="shrink-0" active={quickEstadoActual === "inactivos"} onClick={() => setFilter("estado", "inactivos")}>Inactivos</TableFilterChip>
                  <TableFilterSelect label="Filtrar por UCT" placeholder="Todas las UCT" value={filters.grupo || undefined} onValueChange={(value) => setFilter("grupo", value)} options={filterOptions.grupos} />
                  <TableFilterSelect label="Filtrar por año" placeholder="Todos los años" value={filters.anio || undefined} onValueChange={(value) => setFilter("anio", value)} options={filterOptions.anios} />
                </div>
              </div>
            </TableToolbar>
          }
        />

        <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar artículo de divulgación" message={`¿Está seguro de eliminar ${pendingDelete?.titulo || "este artículo"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando..." />
      </section>

      <SuccessToast open={showSuccess} message={successMessage} onClose={() => setShowSuccess(false)} />
      <SuccessToast open={showError} message={errorMessage} onClose={() => setShowError(false)} variant="error" />
    </>
  );
}
