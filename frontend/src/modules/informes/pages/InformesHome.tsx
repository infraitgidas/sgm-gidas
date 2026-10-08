import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import SuccessToast from "@/components/SuccessToast";
import Table, { TableActionButton, TableActions, TableRowActionButton, TableToolbar } from "@/components/Table";
import type { TableColumn } from "@/components/Table";
import { getErrorMessage } from "@/lib/httpError";
import { useInforme, useInformes } from "@/modules/informes/hooks/useInformes";
import { deleteInforme, informeTipoLabel, informeTipos, type InformeSummary, type InformeTipo } from "@/modules/informes/services/informesService";
import { getMemorias } from "@/modules/memorias/services/memoriasService";
import { formatFecha } from "@/utils/dateTime";

function InformeVinculosExpanded({ tipo, id }: { tipo: "investigadores" | "pid"; id: number }) {
  const detail = useInforme(tipo, id);
  const label = tipo === "pid" ? "proyectos" : "investigadores";
  if (detail.isLoading) return <LoadingSkeleton variant="compact" label={`Cargando ${label} vinculados...`} />;
  if (detail.isError || !detail.data) return <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-rose-700"><span>Lo sentimos, no pudimos recuperar los {label} vinculados. Intente nuevamente.</span><TableActionButton onClick={() => detail.refetch()}>Reintentar</TableActionButton></div>;
  const links = tipo === "pid" ? detail.data.proyectos ?? [] : detail.data.investigadores ?? [];
  if (!links.length) return <p className="text-sm text-slate-500">No hay {label} vinculados a este informe.</p>;
  return <div><h3 className="mb-3 text-sm font-semibold text-slate-900">{tipo === "pid" ? "Proyectos vinculados" : "Investigadores vinculados"}</h3><ul className="space-y-2">{links.map((link) => <li key={link.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm"><span className="font-medium text-slate-900">{String(link.snapshot.nombre_apellido ?? link.snapshot.nombre_proyecto ?? `Registro ${link.id}`)}</span>{link.snapshot.codigo_proyecto && <span className="ml-2 text-slate-500">Código: {link.snapshot.codigo_proyecto}</span>}{link.snapshot.horas_semanales != null && <span className="ml-2 text-slate-500">Horas semanales: {link.snapshot.horas_semanales}</span>}</li>)}</ul></div>;
}

export default function InformesHome() {
  const { tipo: rawTipo } = useParams();
  const tipo = (informeTipos.includes(rawTipo as InformeTipo) ? rawTipo : "uct") as InformeTipo;
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [memoriaId, setMemoriaId] = useState(0);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<InformeSummary | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const informes = useInformes(tipo, page, memoriaId || undefined);
  const memorias = useQuery({ queryKey: ["memorias", "informes-selector"], queryFn: () => getMemorias("all") });
  const remove = useMutation({
    mutationFn: (id: number) => deleteInforme(tipo, id),
    onSuccess: async () => { setPendingDelete(null); setMessage("¡Eliminado con éxito!"); if (informes.data?.data.length === 1 && page > 1) setPage(page - 1); await qc.invalidateQueries({ queryKey: ["informes", tipo] }); },
    onError: (reason) => setError(getErrorMessage(reason, "Lo sentimos, no pudimos completar la operación. Intente nuevamente.")),
  });

  useEffect(() => {
    if (location.state?.successMessage) {
      setMessage(location.state.successMessage);
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  useEffect(() => { setExpandedId(null); }, [tipo]);

  if (!informeTipos.includes(rawTipo as InformeTipo)) return <p role="alert">Tipo de informe no disponible.</p>;
    const columns: TableColumn<InformeSummary>[] = [
      { id: "titulo", header: "Título", align: "center", render: (item) => <span className="font-medium text-slate-900">{item.titulo}</span> },
      { id: "fecha", header: "Fecha de realización", align: "center", render: (item) => formatFecha(item.fecha_realizacion) },
      { id: "autor", header: "Autor", align: "center", priority: "secondary", render: (item) => item.autor ?? "-" },
      { id: "periodo", header: "Período", align: "center", priority: "secondary", render: (item) => <span className="whitespace-nowrap">{formatFecha(item.periodo_inicio)} – {formatFecha(item.periodo_fin)}</span> },
      { id: "acciones", header: "Acciones", align: "center", render: (item) => <div className="flex justify-center"><TableActions>
        <TableRowActionButton action="view" aria-label={`Ver detalle de ${item.titulo}`} onClick={() => navigate(`/informes/${tipo}/${item.id}`)} />
        {item.activo && !item.deleted_at && <TableRowActionButton action="edit" aria-label={`Editar ${item.titulo}`} onClick={() => navigate(`/informes/${tipo}/${item.id}/editar`)} />}
        {item.activo && !item.deleted_at && <TableRowActionButton action="delete" aria-label={`Eliminar ${item.titulo}`} onClick={() => setPendingDelete(item)} />}
      </TableActions></div> },
    ];
    return <section className="min-h-[calc(100vh-120px)] w-full px-4 py-4">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div><h2 className="text-2xl font-semibold md:text-3xl">Informes de {tipo === "pid" ? "Proyectos" : informeTipoLabel[tipo]}</h2><p className="mt-1 text-sm text-slate-500">Consulte los informes por período de Memoria.</p></div>
        <Button size="sm" onClick={() => navigate(`/informes/${tipo}/nuevo`)}>Agregar nuevo</Button>
      </div>
      <Table
        caption={`Listado de informes de ${tipo === "pid" ? "proyectos" : informeTipoLabel[tipo].toLowerCase()}`}
        columns={columns}
        rows={informes.data?.data ?? []}
        getRowId={(item) => item.id}
        density="compact"
        loading={informes.isLoading}
        refreshing={informes.isFetching && !informes.isLoading}
        error={informes.isError}
        onRetry={() => informes.refetch()}
        emptyMessage="No hay informes para este período."
        onRowClick={(item) => navigate(`/informes/${tipo}/${item.id}`)}
        getRowTitle={(item) => `Ver detalle de ${item.titulo}`}
        expandedRowId={expandedId}
        renderExpanded={tipo !== "uct" ? (item) => <InformeVinculosExpanded tipo={tipo} id={item.id} /> : undefined}
        onToggleRow={tipo !== "uct" ? (item) => setExpandedId((current) => current === item.id ? null : item.id) : undefined}
        getExpandLabel={tipo !== "uct" ? (item, expanded) => `${expanded ? "Ocultar" : "Mostrar"} ${tipo === "pid" ? "proyectos" : "investigadores"} vinculados a ${item.titulo}` : undefined}
        page={page}
        totalPages={informes.data?.meta.total_pages ?? 0}
        totalRecords={informes.data?.meta.total ?? 0}
        onPageChange={(nextPage) => { setExpandedId(null); setPage(nextPage); }}
        toolbar={<TableToolbar><label className="flex w-full max-w-sm flex-col gap-1 text-sm font-medium text-slate-700" htmlFor="filtro-memoria-informes"><span>Período de Memoria</span><select id="filtro-memoria-informes" value={memoriaId} onChange={(event) => { setExpandedId(null); setMemoriaId(Number(event.target.value)); setPage(1); }} className="input w-full"><option value={0}>Todos los períodos</option>{(memorias.data ?? []).filter((item) => item.grupo_utn_id && !item.deleted_at).map((item) => <option key={item.id} value={item.id}>{formatFecha(item.periodo_inicio)} a {formatFecha(item.periodo_fin)}</option>)}</select></label>{memorias.isError && <p role="alert" className="text-sm text-rose-700">Lo sentimos, no pudimos recuperar los períodos. <button type="button" onClick={() => memorias.refetch()} className="underline">Reintentar</button></p>}</TableToolbar>}
      />
      <ConfirmDialog open={!!pendingDelete} title="Eliminar informe" message={`¿Desea eliminar ${pendingDelete?.titulo ?? "este informe"}?`} confirmText="Eliminar" onCancel={() => setPendingDelete(null)} onConfirm={() => pendingDelete ? remove.mutateAsync(pendingDelete.id) : undefined} />
      <SuccessToast open={!!message} message={message} onClose={() => setMessage("")} />
      <SuccessToast open={!!error} message={error} variant="error" onClose={() => setError("")} />
    </section>;
}
