import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

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
import {
  applyMemoriaSectionFilter,
  getMemoriaSectionFilter,
} from "@/lib/memoriaSectionFilter";
import { buildMemoriaDetailState } from "@/lib/memoriaNavigation";
import { useRegistrosPropiedad } from "@/modules/produccion/hooks/useRegistrosPropiedad";
import {
  deleteRegistroPropiedad,
  getHistorialRegistroPropiedadById,
  type HistorialRegistroPropiedadItem,
  type RegistroPropiedad,
} from "@/modules/produccion/services/registrosPropiedadServices";
import {
  formatRegistroPropiedadContractValue,
  formatRegistroPropiedadHistoryEntry,
  presentRegistroPropiedadHistoryItems,
} from "@/modules/produccion/utils/registroPropiedadHistory";
import { toTitleCase } from "@/utils/format";

const ITEMS_PER_PAGE = 9;
const HISTORY_PER_PAGE = 3;

const formatFecha = (fecha?: string | null) => {
  if (!fecha) return "—";

  const [y, m, d] = fecha.split("-");
  if (!y || !m || !d) return fecha;

  return `${d}/${m}/${y}`;
};

export default function RegistrosPropiedadLanding() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();

  const puedeCrear = canCreateRecords();

  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [pendingDelete, setPendingDelete] =
    useState<RegistroPropiedad | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [historyPage, setHistoryPage] = useState(1);

  const [filters, setFilters] = useState({
    estado: "",
    tipoRegistro: "",
    fechaRegistro: "",
  });
  const memoriaFilter = useMemo(
    () => getMemoriaSectionFilter(location.state, "registros-propiedad"),
    [location.state]
  );

  const filtroActivos = useMemo<"true" | "false" | "all">(() => {
    if (memoriaFilter) return "all";
    if (filters.estado === "todos") return "all";
    if (filters.estado === "inactivos") return "false";
    return "true";
  }, [filters.estado, memoriaFilter]);

  const { list, isLoading, isError } = useRegistrosPropiedad(
    filtroActivos,
    "asc"
  );
  const scopedList = useMemo(
    () => applyMemoriaSectionFilter(list, memoriaFilter),
    [list, memoriaFilter]
  );

  const opcionesFiltros = useMemo(() => {
    const tiposRegistro = new Set<string>();
    const fechasRegistro = new Set<string>();

    scopedList.forEach((registro) => {
      const tipoRegistro = formatRegistroPropiedadContractValue(
        registro.tipo_registro
      );
      if (tipoRegistro) {
        tiposRegistro.add(toTitleCase(tipoRegistro));
      }
      if (registro.fecha_registro) {
        fechasRegistro.add(formatFecha(registro.fecha_registro));
      }
    });

    return {
      tiposRegistro: Array.from(tiposRegistro).sort(),
      fechasRegistro: Array.from(fechasRegistro).sort(),
    };
  }, [scopedList]);

  const registrosFiltrados = useMemo(() => {
    return scopedList.filter((registro) => {
      const query = searchQuery.toLowerCase().trim();
      const nombre = formatRegistroPropiedadContractValue(
        registro.nombre_articulo
      );
      const tipo = formatRegistroPropiedadContractValue(registro.tipo_registro);
      const organismo = formatRegistroPropiedadContractValue(
        registro.organismo_registrante
      );
      const matchesSearch =
        !query ||
        nombre.toLowerCase().includes(query) ||
        tipo.toLowerCase().includes(query) ||
        String(registro.fecha_registro ?? "").toLowerCase().includes(query) ||
        organismo.toLowerCase().includes(query);
      const matchTipoRegistro =
        !filters.tipoRegistro ||
        toTitleCase(tipo) === filters.tipoRegistro;
      const matchFechaRegistro =
        !filters.fechaRegistro ||
        formatFecha(registro.fecha_registro) === filters.fechaRegistro;

      return matchesSearch && matchTipoRegistro && matchFechaRegistro;
    });
  }, [scopedList, filters, searchQuery]);

  const totalPages = Math.ceil(registrosFiltrados.length / ITEMS_PER_PAGE);
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return registrosFiltrados.slice(start, start + ITEMS_PER_PAGE);
  }, [currentPage, registrosFiltrados]);
  const expandedItem =
    expandedRow === null
      ? undefined
      : scopedList.find((registro) => registro.id === expandedRow);
  const history = useQuery({
    queryKey: ["registro-propiedad-historial", expandedItem?.id],
    queryFn: () => getHistorialRegistroPropiedadById(expandedItem!.id),
    enabled: Boolean(expandedItem),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    setCurrentPage(1);
    setExpandedRow(null);
  }, [filters, searchQuery]);

  useEffect(() => {
    if (location.state?.successMessage) {
      setSuccessMessage(location.state.successMessage);
      setShowSuccess(true);
      navigate(location.pathname, { replace: true });
    }
  }, [location.state, navigate, location.pathname]);

  const setQuickEstado = (estado: "" | "todos" | "inactivos") => {
    setFilters((prev) => ({ ...prev, estado }));
  };
  const quickEstadoActual =
    filters.estado === "todos"
      ? "todos"
      : filters.estado === "inactivos"
        ? "inactivos"
        : "activos";

  const confirmDelete = async () => {
    if (!pendingDelete || pendingDelete.deleted_at || !canDeleteRecords()) return;

    try {
      await deleteRegistroPropiedad(pendingDelete.id);
      await queryClient.invalidateQueries({
        queryKey: ["registros-propiedad"],
      });
      setPendingDelete(null);
      setSuccessMessage("Registro eliminado con éxito.");
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
        <div role="alert" className="flex items-center gap-3 text-sm text-rose-700">
          <span>
            Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.
          </span>
          <TableActionButton onClick={() => history.refetch()}>
            Reintentar
          </TableActionButton>
        </div>
      );
    }

    const entries = presentRegistroPropiedadHistoryItems(
      (history.data ?? []) as HistorialRegistroPropiedadItem[]
    );
    if (!entries.length) {
      return (
        <p className="text-sm text-slate-500">No hay cambios registrados.</p>
      );
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
            const presentation = formatRegistroPropiedadHistoryEntry(entry);
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

  const columns: TableColumn<RegistroPropiedad>[] = [
    {
      id: "nombre",
      header: "Registro de propiedad",
      render: (registro) => (
        <span className="font-medium text-slate-900">
          {formatRegistroPropiedadContractValue(registro.nombre_articulo) ||
            "—"}
        </span>
      ),
    },
    {
      id: "tipo",
      header: "Tipo",
      priority: "secondary",
      render: (registro) =>
        toTitleCase(
          formatRegistroPropiedadContractValue(registro.tipo_registro)
        ) || "—",
    },
    {
      id: "organismo",
      header: "Organismo registrante",
      priority: "secondary",
      render: (registro) =>
        toTitleCase(
          formatRegistroPropiedadContractValue(registro.organismo_registrante)
        ) || "—",
    },
    {
      id: "fecha",
      header: "Fecha de registro",
      priority: "tertiary",
      render: (registro) => formatFecha(registro.fecha_registro),
    },
    {
      id: "estado",
      header: "Estado",
      render: (registro) => {
        const activo = !registro.deleted_at;
        return (
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-medium ${
              activo ? "text-emerald-700" : "text-rose-700"
            }`}
          >
            <span
              aria-hidden="true"
              className={`h-2 w-2 rounded-full ${
                activo ? "bg-emerald-500" : "bg-rose-500"
              }`}
            />
            {activo ? "Activo" : "Inactivo"}
          </span>
        );
      },
    },
    {
      id: "acciones",
      header: "Acciones",
      align: "right",
      render: (registro) => (
        <TableActions>
          <TableRowActionButton
            action="view"
            aria-label={`Ver detalle de ${formatRegistroPropiedadContractValue(registro.nombre_articulo) || "registro"}`}
            onClick={() =>
              navigate(`/registros-propiedad/${registro.id}`, {
                state: buildMemoriaDetailState(location),
              })
            }
          />
          {!registro.deleted_at && canEditRecords() && (
            <TableRowActionButton
              action="edit"
              aria-label={`Editar ${formatRegistroPropiedadContractValue(registro.nombre_articulo) || "registro"}`}
              onClick={() =>
                navigate(`/registros-propiedad/${registro.id}/editar`)
              }
            />
          )}
          {!registro.deleted_at && canDeleteRecords() && (
            <TableRowActionButton
              action="delete"
              aria-label={`Eliminar ${formatRegistroPropiedadContractValue(registro.nombre_articulo) || "registro"}`}
              onClick={() => setPendingDelete(registro)}
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
            <h2 className="text-2xl font-semibold md:text-3xl">
              Registros de Propiedad
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Gestione los registros, sus organismos y estados.
            </p>
          </div>
          {puedeCrear && (
            <Button
              size="sm"
              onClick={() => navigate("/registros-propiedad/nuevo")}
            >
              Agregar nuevo
            </Button>
          )}
        </div>

        {memoriaFilter && (
          <div className="mb-4">
            <MemoriaFilterBanner filter={memoriaFilter} />
          </div>
        )}

        <Table
          caption="Listado de registros de propiedad"
          columns={columns}
          rows={paginatedItems}
          getRowId={(registro) => registro.id}
          density="compact"
          loading={isLoading}
          error={isError}
          emptyMessage="No hay registros de propiedad que coincidan con los filtros."
          onRowClick={(registro) =>
            navigate(`/registros-propiedad/${registro.id}`, {
              state: buildMemoriaDetailState(location),
            })
          }
          getRowTitle={(registro) =>
            `Ver detalle de ${formatRegistroPropiedadContractValue(registro.nombre_articulo) || "registro"}`
          }
          expandedRowId={expandedRow}
          renderExpanded={renderHistory}
          onToggleRow={(registro) => {
            setExpandedRow((current) =>
              current === registro.id ? null : registro.id
            );
            setHistoryPage(1);
          }}
          getExpandLabel={(registro, expanded) =>
            `${expanded ? "Ocultar" : "Mostrar"} historial de ${
              formatRegistroPropiedadContractValue(registro.nombre_articulo) ||
              "registro"
            }`
          }
          page={currentPage}
          totalPages={totalPages}
          totalRecords={registrosFiltrados.length}
          onPageChange={(nextPage) => {
            setExpandedRow(null);
            setCurrentPage(nextPage);
          }}
          toolbar={
            <TableToolbar>
              <div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center">
                <TableSearch
                  label="Buscar registros de propiedad"
                  placeholder="Buscar por nombre, tipo u organismo"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                <div
                  className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto pb-1 whitespace-nowrap"
                  aria-label="Filtros de registros de propiedad"
                >
                  <span className="shrink-0 text-xs font-medium text-slate-500">
                    Estado
                  </span>
                  <TableFilterChip
                    className="shrink-0"
                    active={quickEstadoActual === "activos"}
                    onClick={() => setQuickEstado("")}
                  >
                    Activos
                  </TableFilterChip>
                  <TableFilterChip
                    className="shrink-0"
                    active={quickEstadoActual === "todos"}
                    onClick={() => setQuickEstado("todos")}
                  >
                    Todos
                  </TableFilterChip>
                  <TableFilterChip
                    className="shrink-0"
                    active={quickEstadoActual === "inactivos"}
                    onClick={() => setQuickEstado("inactivos")}
                  >
                    Inactivos
                  </TableFilterChip>
                  <TableFilterSelect
                    label="Filtrar por tipo de registro"
                    placeholder="Todos los tipos"
                    value={filters.tipoRegistro || undefined}
                    onValueChange={(value) =>
                      setFilters((current) => ({
                        ...current,
                        tipoRegistro: value ?? "",
                      }))
                    }
                    options={opcionesFiltros.tiposRegistro.map((tipo) => ({
                      value: tipo,
                      label: tipo,
                    }))}
                  />
                  <TableFilterSelect
                    label="Filtrar por fecha de registro"
                    placeholder="Todas las fechas"
                    value={filters.fechaRegistro || undefined}
                    onValueChange={(value) =>
                      setFilters((current) => ({
                        ...current,
                        fechaRegistro: value ?? "",
                      }))
                    }
                    options={opcionesFiltros.fechasRegistro.map((fecha) => ({
                      value: fecha,
                      label: fecha,
                    }))}
                  />
                </div>
              </div>
            </TableToolbar>
          }
        />

        <ConfirmDialog
          open={Boolean(pendingDelete)}
          title="Eliminar registro de propiedad"
          message={`¿Está seguro de eliminar ${formatRegistroPropiedadContractValue(pendingDelete?.nombre_articulo) || "este registro"}?`}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
          loadingText="Eliminando..."
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
