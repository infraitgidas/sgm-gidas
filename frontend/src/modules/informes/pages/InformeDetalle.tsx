import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import SuccessToast from "@/components/SuccessToast";
import { useInforme, useInformeHistorial } from "@/modules/informes/hooks/useInformes";
import { informeTipoLabel, informeTipos, type InformeTipo } from "@/modules/informes/services/informesService";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";

export default function InformeDetalle() {
  const { tipo: rawTipo, id } = useParams();
  const tipo = (informeTipos.includes(rawTipo as InformeTipo) ? rawTipo : "uct") as InformeTipo;
  const recordId = Number(id);
  const navigate = useNavigate();
  const location = useLocation();
  const [message, setMessage] = useState("");
  const informe = useInforme(tipo, Number.isInteger(recordId) && recordId > 0 ? recordId : undefined);
  const history = useInformeHistorial(tipo, Number.isInteger(recordId) && recordId > 0 ? recordId : undefined);

  useEffect(() => {
    if (location.state?.successMessage) {
      setMessage(location.state.successMessage);
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  if (!informeTipos.includes(rawTipo as InformeTipo)) return <p role="alert">Tipo de informe no disponible.</p>;
  if (informe.isLoading) return <LoadingSkeleton variant="detail" label="Cargando informe..." />;
  if (informe.isError || !informe.data) return <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-700">Lo sentimos, no pudimos recuperar la información. <button type="button" className="underline" onClick={() => informe.refetch()}>Intente nuevamente</button>.</p>;
  const data = informe.data;
  const links = tipo === "pid" ? data.proyectos ?? [] : data.investigadores ?? [];
  return <section className="flex flex-col gap-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold leading-none md:text-3xl">{data.titulo}</h2>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-fit rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-600">Informe de {informeTipoLabel[tipo]}</span>
          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${data.activo && !data.deleted_at ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>{data.activo && !data.deleted_at ? "ACTIVO" : "INACTIVO"}</span>
        </div>
      </div>
      {data.activo && !data.deleted_at && <Button size="sm" onClick={() => navigate(`/informes/${tipo}/${data.id}/editar`)}>Editar</Button>}
    </div>
    <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
      <div className="space-y-3 text-sm text-slate-500 md:text-base">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <p><span className="font-semibold text-slate-800">Período de Memoria:</span> {formatFecha(data.periodo_inicio)} – {formatFecha(data.periodo_fin)}</p>
            <p><span className="font-semibold text-slate-800">Fecha de realización:</span> {formatFecha(data.fecha_realizacion)}</p>
            <p><span className="font-semibold text-slate-800">Autor:</span> {data.autor ?? "-"}</p>
          </div>
        </div>
        <div><h3 className="pt-3 text-xl font-semibold text-slate-800">Contenido del informe</h3><div className="mt-4 space-y-6">{(["resumen", "actividades", "resultados", "observaciones"] as const).map((field) => <div key={field}><h4 className="text-lg font-semibold capitalize text-slate-800">{field}</h4><p className="mt-2 whitespace-pre-wrap leading-relaxed text-slate-600">{data[field]}</p></div>)}</div></div>
        {tipo !== "uct" && <div><h3 className="pt-3 text-base font-semibold text-slate-800">{tipo === "pid" ? "Proyectos vinculados" : "Investigadores vinculados"}</h3><ul className="mt-3 space-y-2">{links.map((link) => <li key={link.id} className="rounded-lg border border-slate-200 bg-white p-3"><p className="font-medium text-slate-800">{String(link.snapshot.nombre_apellido ?? link.snapshot.nombre_proyecto ?? `Registro ${link.id}`)}</p>{link.snapshot.codigo_proyecto && <p>Código: {link.snapshot.codigo_proyecto}</p>}{link.snapshot.descripcion_proyecto && <p className="whitespace-pre-wrap">Descripción: {link.snapshot.descripcion_proyecto}</p>}{link.snapshot.fecha_inicio && <p>Inicio: {formatFecha(String(link.snapshot.fecha_inicio))}</p>}{link.snapshot.fecha_fin && <p>Fin: {formatFecha(String(link.snapshot.fecha_fin))}</p>}{link.snapshot.fecha_alta_grupo && <p>Alta en el grupo: {formatFecha(String(link.snapshot.fecha_alta_grupo))}</p>}{link.snapshot.horas_semanales != null && <p>Horas semanales: {link.snapshot.horas_semanales}</p>}</li>)}</ul></div>}
        <div><h3 className="pt-3 text-base font-semibold text-slate-800">UCT</h3><p className="mt-2"><span className="font-semibold text-slate-800">Nombre:</span> {data.uct_snapshot.nombre_sigla_grupo}</p><p className="mt-1"><span className="font-semibold text-slate-800">Correo:</span> {data.uct_snapshot.mail || "-"}</p></div>
      </div>
    </article>
    <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm"><div className="mb-4"><h3 className="text-lg font-semibold text-slate-800">Auditoría</h3><p className="mt-1 text-xs text-slate-500">{data.titulo}</p></div><div className="space-y-2 text-sm text-slate-500 md:text-base"><p><span className="font-semibold text-slate-800">Creado por:</span> {data.created_by_nombre ?? "-"}</p><p><span className="font-semibold text-slate-800">Fecha de creación:</span> {formatFechaHora(data.created_at)}</p><p><span className="font-semibold text-slate-800">Actualizado por:</span> {data.updated_by_nombre ?? "-"}</p><p><span className="font-semibold text-slate-800">Fecha de actualización:</span> {data.updated_at ? formatFechaHora(data.updated_at) : "-"}</p></div></article>
    {history.isError && <p role="alert" className="text-rose-700">Lo sentimos, no pudimos recuperar el historial. <button type="button" className="underline" onClick={() => history.refetch()}>Intente nuevamente</button>.</p>}
    <HistorialCambiosCard subtitle={data.titulo} items={history.data ?? []} isLoading={history.isLoading} pageSize={3} updatedAt={data.updated_at} updatedByName={data.updated_by_nombre} formatItemPresentation={(item) => {
      if (item.campo !== "vinculos_ids" || !item.valor_nuevo || typeof item.valor_nuevo !== "object") return null;
      const value = item.valor_nuevo as { accion?: string; detalle?: { nombre?: string } };
      return { title: value.accion === "desvincular" ? "Registro desvinculado" : "Registro vinculado", description: value.detalle?.nombre ?? "Registro asociado" };
    }} />
    <div className="flex justify-start pt-4"><Button variant="secondary" size="sm" onClick={() => navigate(`/informes/${tipo}`)}>Volver</Button></div>
    <SuccessToast open={!!message} message={message} onClose={() => setMessage("")} />
  </section>;
}
