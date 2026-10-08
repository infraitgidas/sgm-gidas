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
import {
  buildMemoriaDetailState,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";
import { getTiposVisita } from "@/modules/grupo/services/tiposVisitaServices";
import {
  eliminarVisitante,
  getHistorialVisitanteById,
  getVisitantes,
  type HistorialVisitanteItem,
  type Visitante,
} from "@/modules/grupo/services/visitantesServices";
import {
  formatVisitHistoryEntry,
  presentVisitHistoryItems,
} from "@/modules/grupo/utils/visitHistory";
import { getCivilYear } from "@/utils/dateTime";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;

const formatDate = (dateStr?: string | null) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr ?? "");
  return match ? `${match[3]}/${match[2]}/${match[1]}` : dateStr || "-";
};

export default function VisitantesHome() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();

  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    estado: "",
    tipoVisita: "",
    procedencia: "",
    anio: "",
  });
  const [page, setPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [pendingDelete, setPendingDelete] = useState<Visitante | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const memoriaFilter = useMemo(
    () => getMemoriaSectionFilter(location.state, "visitas-academicas"),
    [location.state]
  );
  const activos = useMemo<"true" | "false" | "all">(() => {
    if (memoriaFilter || filters.estado === "todos") return "all";
    if (filters.estado === "inactivos") return "false";
    return "true";
  }, [filters.estado, memoriaFilter]);

  const visitas = useQuery({
    queryKey: ["visitantes", activos],
    queryFn: () => getVisitantes(activos),
    staleTime: 60_000,
  });
  const tipos = useQuery({
    queryKey: ["tipos-visita"],
    queryFn: getTiposVisita,
    staleTime: 60_000,
  });
  const scopedList = useMemo(
    () => applyMemoriaSectionFilter(visitas.data ?? [], memoriaFilter),
    [memoriaFilter, visitas.data]
  );
  const filterOptions = useMemo(() => {
    const procedencias = new Set<string>();
    const anios = new Set<number>();

    scopedList.forEach((visita) => {
      if (visita.procedencia.trim()) procedencias.add(visita.procedencia.trim());
      const anio = getCivilYear(visita.fecha);
      if (anio) anios.add(anio);
    });

    return {
      procedencias: Array.from(procedencias)
        .sort((a, b) => a.localeCompare(b, "es"))
        .map((value) => ({ value, label: value })),
      anios: Array.from(anios)
        .sort((a, b) => b - a)
        .map((value) => ({ value: String(value), label: String(value) })),
    };
  }, [scopedList]);
  const tiposVisitaMap = useMemo(
    () => new Map((tipos.data ?? []).map((tipo) => [tipo.id, tipo.nombre])),
    [tipos.data]
  );

  const filteredList = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase("es");

    return scopedList.filter((visita) => {
      const searchable = [
        visita.razon,
        visita.tipo_visita?.nombre,
        visita.procedencia,
        visita.fecha,
        visita.grupo,
      ];
      const matchesSearch =
        !query ||
        searchable.some((value) =>
          String(value ?? "").toLocaleLowerCase("es").includes(query)
        );

      return (
        matchesSearch &&
        (!filters.tipoVisita ||
          String(visita.tipo_visita_id) === filters.tipoVisita) &&
        (!filters.procedencia || visita.procedencia === filters.procedencia) &&
        (!filters.anio || getCivilYear(visita.fecha) === Number(filters.anio))
      );
    });
  }, [filters, scopedList, searchQuery]);

  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const paginated = useMemo(
    () =>
      filteredList.slice(
        (page - 1) * ITEMS_PER_PAGE,
        page * ITEMS_PER_PAGE
      ),
    [filteredList, page]
  );
  const expandedVisit =
    expandedRow === null
      ? undefined
      : scopedList.find((visita) => visita.id === expandedRow);
  const history = useQuery({
    queryKey: ["visitante-historial", expandedVisit?.id],
    queryFn: () => getHistorialVisitanteById(expandedVisit!.id),
    enabled: Boolean(expandedVisit),
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
    navigate(location.pathname, {
      replace: true,
      state: stripSuccessMessageState(location.state),
    });
  }, [location.pathname, location.state, navigate]);

  const setFilter = (field: keyof typeof filters, value?: string) =>
    setFilters((current) => ({ ...current, [field]: value ?? "" }));
  const stateFilter =
    filters.estado === "todos"
      ? "todos"
      : filters.estado === "inactivos"
        ? "inactivos"
        : "activos";

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || !canDeleteRecords()) return;

    try {
      await eliminarVisitante(pendingDelete.id);
      await queryClient.invalidateQueries({ queryKey: ["visitantes"] });
      setPendingDelete(null);
      setSuccessMessage("Visita eliminada con éxito.");
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
      return (
        <LoadingSkeleton variant="compact" label="Cargando historial..." />
      );
    }

    if (history.isError) {
      return (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-rose-700">
          <span>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</span>
          <TableActionButton onClick={() => void history.refetch()}>
            Reintentar
          </TableActionButton>
        </div>
      );
    }

    const entries = presentVisitHistoryItems(
      (history.data ?? []) as HistorialVisitanteItem[]
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
        <h3 className="mb-3 text-sm font-semibold text-slate-900">
          Historial de cambios
        </h3>
        <ul className="space-y-2">
          {visible.map((entry) => {
            const presentation = formatVisitHistoryEntry(entry, {
              tiposVisita: tiposVisitaMap,
              visita: expandedVisit,
            });
            return (
              <li
                key={entry.id}
                className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <span className="block font-medium text-slate-800">
                  {presentation.title}
                </span>
                <span className="mt-1 block text-slate-600">
                  {presentation.description}
                </span>
                {entry.usuario_nombre && (
                  <span className="mt-1 block text-xs text-slate-500">
                    Por {entry.usuario_nombre}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
        {pages > 1 && (
          <nav aria-label="Paginación del historial" className="mt-3 flex gap-2">
            <TableActionButton
              disabled={historyPage === 1}
              onClick={() => setHistoryPage((value) => value - 1)}
            >
              Anterior
            </TableActionButton>
            <span className="self-center text-xs text-slate-500">
              Página {historyPage} de {pages}
            </span>
            <TableActionButton
              disabled={historyPage === pages}
              onClick={() => setHistoryPage((value) => value + 1)}
            >
              Siguiente
            </TableActionButton>
          </nav>
        )}
      </div>
    );
  };

  const columns: TableColumn<Visitante>[] = [
    {
      id: "razon",
      header: "Razón de la visita",
      render: (visita) => (
        <span className="font-medium text-slate-900">{visita.razon || "-"}</span>
      ),
    },
    {
      id: "tipo",
      header: "Tipo de visita",
      render: (visita) => (
        <span className="inline-flex rounded-full bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700">
          {visita.tipo_visita?.nombre || "Sin tipo informado"}
        </span>
      ),
    },
    {
      id: "procedencia",
      header: "Procedencia u origen",
      priority: "secondary",
      render: (visita) => visita.procedencia || "-",
    },
    {
      id: "fecha",
      header: "Fecha",
      priority: "tertiary",
      render: (visita) => formatDate(visita.fecha),
    },
    {
      id: "estado",
      header: "Estado",
      render: (visita) => {
        const active = !visita.deleted_at;
        return (
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-medium ${
              active ? "text-emerald-700" : "text-rose-700"
            }`}
          >
            <span
              aria-hidden="true"
              className={`h-2 w-2 rounded-full ${
                active ? "bg-emerald-500" : "bg-rose-500"
              }`}
            />
            {active ? "Activo" : "Inactivo"}
          </span>
        );
      },
    },
    {
      id: "acciones",
      header: "Acciones",
      align: "right",
      render: (visita) => {
        const active = !visita.deleted_at;
        const label = visita.razon || "la visita";
        return (
          <TableActions>
            <TableRowActionButton
              action="view"
              aria-label={`Ver detalle de ${label}`}
              onClick={() =>
                navigate(`/visitantes/${visita.id}`, {
                  state: buildMemoriaDetailState(location),
                })
              }
            />
            {active && canEditRecords() && (
              <TableRowActionButton
                action="edit"
                aria-label={`Editar ${label}`}
                onClick={() => navigate(`/visitantes/${visita.id}/editar`)}
              />
            )}
            {active && canDeleteRecords() && (
              <TableRowActionButton
                action="delete"
                aria-label={`Eliminar ${label}`}
                onClick={() => setPendingDelete(visita)}
              />
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
            <h2 className="text-2xl font-semibold md:text-3xl">Visitas</h2>
            <p className="mt-1 text-sm text-slate-500">
              Gestione el propósito, el tipo y la procedencia de las visitas institucionales.
            </p>
          </div>
          {canCreateRecords() && (
            <Button size="sm" onClick={() => navigate("/visitantes/nuevo")}>
              Agregar nueva
            </Button>
          )}
        </div>

        {memoriaFilter && (
          <div className="mb-4">
            <MemoriaFilterBanner filter={memoriaFilter} />
          </div>
        )}

        <Table
          caption="Listado de visitas"
          columns={columns}
          rows={paginated}
          getRowId={(visita) => visita.id}
          density="compact"
          loading={visitas.isLoading}
          refreshing={visitas.isFetching && !visitas.isLoading}
          error={visitas.isError}
          onRetry={() => void visitas.refetch()}
          emptyMessage="No hay visitas que coincidan con la búsqueda y los filtros."
          onRowClick={(visita) =>
            navigate(`/visitantes/${visita.id}`, {
              state: buildMemoriaDetailState(location),
            })
          }
          getRowTitle={(visita) => `Ver detalle de ${visita.razon || "la visita"}`}
          expandedRowId={expandedRow}
          renderExpanded={renderHistory}
          onToggleRow={(visita) => {
            setExpandedRow((current) => (current === visita.id ? null : visita.id));
            setHistoryPage(1);
          }}
          getExpandLabel={(visita, expanded) =>
            `${expanded ? "Ocultar" : "Mostrar"} historial de ${
              visita.razon || "la visita"
            }`
          }
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
                <TableSearch
                  label="Buscar visitas"
                  placeholder="Buscar por razón, tipo, procedencia, fecha o grupo"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                <div
                  className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent"
                  aria-label="Filtros de visitas"
                >
                  <span className="shrink-0 text-xs font-medium text-slate-500">
                    Estado
                  </span>
                  <TableFilterChip
                    className="shrink-0"
                    active={stateFilter === "activos"}
                    onClick={() => setFilter("estado", "")}
                  >
                    Activos
                  </TableFilterChip>
                  <TableFilterChip
                    className="shrink-0"
                    active={stateFilter === "todos"}
                    onClick={() => setFilter("estado", "todos")}
                  >
                    Todos
                  </TableFilterChip>
                  <TableFilterChip
                    className="shrink-0"
                    active={stateFilter === "inactivos"}
                    onClick={() => setFilter("estado", "inactivos")}
                  >
                    Inactivos
                  </TableFilterChip>
                  <TableFilterSelect
                    label="Filtrar por tipo de visita"
                    placeholder="Todos los tipos"
                    value={filters.tipoVisita || undefined}
                    onValueChange={(value) => setFilter("tipoVisita", value)}
                    options={(tipos.data ?? []).map((tipo) => ({
                      value: String(tipo.id),
                      label: tipo.nombre,
                    }))}
                    disabled={tipos.isLoading || tipos.isError}
                  />
                  <TableFilterSelect
                    label="Filtrar por procedencia"
                    placeholder="Todas las procedencias"
                    value={filters.procedencia || undefined}
                    onValueChange={(value) => setFilter("procedencia", value)}
                    options={filterOptions.procedencias}
                  />
                  <TableFilterSelect
                    label="Filtrar por año"
                    placeholder="Todos los años"
                    value={filters.anio || undefined}
                    onValueChange={(value) => setFilter("anio", value)}
                    options={filterOptions.anios}
                  />
                </div>
              </div>
            </TableToolbar>
          }
        />

        {tipos.isError && (
          <div role="alert" className="mt-3 flex flex-wrap items-center gap-3 text-sm text-rose-700">
            <span>No pudimos recuperar los tipos para el filtro. Intente nuevamente.</span>
            <TableActionButton onClick={() => void tipos.refetch()}>
              Reintentar
            </TableActionButton>
          </div>
        )}

        <ConfirmDialog
          open={Boolean(pendingDelete)}
          title="Eliminar visita"
          message={`¿Está seguro de eliminar ${pendingDelete?.razon || "esta visita"}?`}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
          loadingText="Eliminando…"
        />
      </section>

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
