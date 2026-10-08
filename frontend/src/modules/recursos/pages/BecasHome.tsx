import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import SuccessToast from "@/components/SuccessToast";
import Table, { TableActions, TableFilterChip, TableRowActionButton, TableSearch, TableToolbar } from "@/components/Table";
import type { TableColumn } from "@/components/Table";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import { useBecasPage } from "@/modules/recursos/hooks/useBecasPage";
import { deleteBeca, type Beca } from "@/modules/recursos/services/becasService";
import { formatFecha } from "@/utils/dateTime";

export default function BecasHome() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();
  const [page, setPage] = useState(1);
  const [estado, setEstado] = useState<"true" | "false" | "all">("true");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Beca | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const becas = useBecasPage(page, estado, query);
  const rows = becas.data?.data ?? [];

  useEffect(() => {
    const timer = window.setTimeout(() => { setQuery(search.trim()); setPage(1); }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (becas.data && page > Math.max(1, becas.data.meta.total_pages)) setPage(Math.max(1, becas.data.meta.total_pages));
  }, [becas.data, page]);

  useEffect(() => {
    const success = (location.state as { successMessage?: string } | null)?.successMessage;
    if (!success) return;
    setMessage(success);
    navigate(location.pathname, { replace: true });
  }, [location.pathname, location.state, navigate]);

  const columns: TableColumn<Beca>[] = [
    { id: "nombre", header: "Beca", render: (item) => <div className="min-w-0"><span className="block font-semibold text-slate-900">{item.nombre_beca}</span><span className="mt-0.5 block max-w-sm truncate text-xs text-slate-500" title={item.descripcion || undefined}>{item.descripcion || "Sin descripción"}</span></div> },
    { id: "fuente", header: "Fuente de financiamiento", priority: "secondary", render: (item) => <span className="text-slate-600">{item.fuente_financiamiento?.nombre ?? "Sin fuente asignada"}</span> },
    { id: "becarios", header: "Becarios", priority: "tertiary", render: (item) => <span className="inline-flex min-w-7 justify-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold tabular-nums text-slate-700">{item.becarios?.length ?? 0}</span> },
    { id: "alta", header: "Alta en el grupo", priority: "tertiary", render: (item) => <span className="whitespace-nowrap text-slate-600">{formatFecha(item.fecha_alta_grupo)}</span> },
    { id: "estado", header: "Estado", render: (item) => { const active = !item.deleted_at; return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${active ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}><span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${active ? "bg-emerald-500" : "bg-rose-500"}`} />{active ? "Activa" : "Inactiva"}</span>; } },
    { id: "acciones", header: "Acciones", align: "right", render: (item) => <TableActions>
      <TableRowActionButton action="view" aria-label={`Ver beca ${item.nombre_beca}`} onClick={() => navigate(`/becas/${item.id}`)} />
      {!item.deleted_at && canEditRecords() && <TableRowActionButton action="edit" aria-label={`Editar beca ${item.nombre_beca}`} onClick={() => navigate(`/becas/${item.id}/editar`)} />}
      {!item.deleted_at && canDeleteRecords() && <TableRowActionButton action="delete" aria-label={`Eliminar beca ${item.nombre_beca}`} onClick={() => setPendingDelete(item)} />}
    </TableActions> },
  ];

  const confirmDelete = async () => {
    if (!pendingDelete || !canDeleteRecords()) return;
    try {
      await deleteBeca(pendingDelete.id);
      await queryClient.invalidateQueries({ queryKey: ["becas"] });
      setMessage("Beca eliminada con éxito.");
      setPendingDelete(null);
    } catch (cause) {
      setError(getErrorMessage(cause, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
      setPendingDelete(null);
    }
  };

  return <>
    <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div><h2 className="text-2xl font-semibold md:text-3xl">Becas</h2><p className="mt-1 text-sm text-slate-500">Consulte las becas disponibles y los becarios vinculados.</p></div>
        {canCreateRecords() && <Button size="sm" onClick={() => navigate("/becas/nueva")}>Agregar nueva</Button>}
      </div>
      <Table caption="Listado de becas" columns={columns} rows={rows} getRowId={(item) => item.id}
        density="compact" loading={becas.isLoading} refreshing={becas.isFetching && !becas.isLoading}
        error={becas.isError} onRetry={() => { void becas.refetch(); }}
        emptyMessage="No hay becas que coincidan con la búsqueda y los filtros."
        onRowClick={(item) => navigate(`/becas/${item.id}`)} getRowTitle={(item) => `Ver beca ${item.nombre_beca}`}
        page={page} totalPages={becas.data?.meta.total_pages ?? 0} totalRecords={becas.data?.meta.total ?? 0}
        onPageChange={setPage}
        toolbar={<TableToolbar><div className="flex w-full flex-col gap-3 xl:flex-row xl:items-center">
          <TableSearch label="Buscar becas" placeholder="Buscar por nombre o descripción" value={search} onChange={(event) => setSearch(event.target.value)} />
          <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto py-1 whitespace-nowrap [scrollbar-color:rgb(203_213_225)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-track]:bg-transparent" aria-label="Filtros de becas">
            <span className="shrink-0 text-xs font-medium text-slate-500">Estado</span>
            <TableFilterChip className="shrink-0" active={estado === "true"} onClick={() => { setEstado("true"); setPage(1); }}>Activas</TableFilterChip>
            <TableFilterChip className="shrink-0" active={estado === "all"} onClick={() => { setEstado("all"); setPage(1); }}>Todas</TableFilterChip>
            <TableFilterChip className="shrink-0" active={estado === "false"} onClick={() => { setEstado("false"); setPage(1); }}>Inactivas</TableFilterChip>
          </div>
        </div></TableToolbar>}
      />
      <ConfirmDialog open={Boolean(pendingDelete)} title="Eliminar beca" message={`¿Está seguro de eliminar ${pendingDelete?.nombre_beca ?? "esta beca"}?`} onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete} loadingText="Eliminando..." />
    </section>
    <SuccessToast open={Boolean(message)} message={message} onClose={() => setMessage("")} />
    <SuccessToast open={Boolean(error)} message={error} onClose={() => setError("")} variant="error" />
  </>;
}
