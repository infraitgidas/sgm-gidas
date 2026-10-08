import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Button from "@/components/Button";
import Calendar from "@/components/Calendar";
import Field from "@/components/Field";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors, focusFieldErrors, getErrorMessage } from "@/lib/httpError";
import { useInforme, useInformeCandidates } from "@/modules/informes/hooks/useInformes";
import { createInforme, informeTipoLabel, informeTipos, updateInforme, type InformePayload, type InformeTipo } from "@/modules/informes/services/informesService";
import { diffInforme, validateInforme } from "@/modules/informes/utils/validation";
import { getMemorias } from "@/modules/memorias/services/memoriasService";
import { formatFecha, parseCivilDate, toCivilDateString } from "@/utils/dateTime";

const emptyText = { titulo: "", resumen: "", actividades: "", resultados: "", observaciones: "" };
const sections = ["resumen", "actividades", "resultados", "observaciones"] as const;

export default function InformeForm() {
  const { tipo: rawTipo, id } = useParams();
  const tipo = (informeTipos.includes(rawTipo as InformeTipo) ? rawTipo : "uct") as InformeTipo;
  const editing = !!id;
  const recordId = id ? Number(id) : undefined;
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const detail = useInforme(tipo, recordId);
  const memorias = useQuery({ queryKey: ["memorias", "informes-selector"], queryFn: () => getMemorias("all") });
  const [memoriaId, setMemoriaId] = useState(0);
  const [date, setDate] = useState<Date | null>(null);
  const [text, setText] = useState(emptyText);
  const [ids, setIds] = useState<number[]>(() => {
    const projectId = Number(new URLSearchParams(location.search).get("proyectoId"));
    return !editing && tipo === "pid" && Number.isInteger(projectId) && projectId > 0 ? [projectId] : [];
  });
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [choicePage, setChoicePage] = useState(1);
  const [selectedNames, setSelectedNames] = useState<Record<number, string>>(() => {
    const projectId = Number(new URLSearchParams(location.search).get("proyectoId"));
    const projectName = (location.state as { projectName?: string } | null)?.projectName;
    return projectId > 0 && projectName ? { [projectId]: projectName } : {};
  });
  const candidates = useInformeCandidates(tipo, memoriaId, debouncedSearch, choicePage);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const hydratedId = useRef<number | null>(null);
  const candidateInputs = useRef<Record<number, HTMLInputElement | null>>({});

  useEffect(() => {
    const timer = window.setTimeout(() => { setDebouncedSearch(search); setChoicePage(1); }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!detail.data || hydratedId.current === detail.data.id) return;
    hydratedId.current = detail.data.id;
    setMemoriaId(detail.data.memoria_id);
    setDate(parseCivilDate(detail.data.fecha_realizacion));
    setText({ titulo: detail.data.titulo, resumen: detail.data.resumen, actividades: detail.data.actividades, resultados: detail.data.resultados, observaciones: detail.data.observaciones });
    const links = (tipo === "pid" ? detail.data.proyectos : detail.data.investigadores) ?? [];
    setIds(links.map((item) => item.id));
    setSelectedNames(Object.fromEntries(links.map((item) => [item.id, String(item.snapshot.nombre_apellido ?? item.snapshot.nombre_proyecto ?? `Registro ${item.id}`)])));
  }, [detail.data, tipo]);

  const previousLinks = (tipo === "pid" ? detail.data?.proyectos : detail.data?.investigadores) ?? [];

  const mutation = useMutation({ mutationFn: async (payload: InformePayload) => {
    if (!editing) return createInforme(tipo, payload);
    const original = detail.data!;
    const before: InformePayload = { memoria_id: original.memoria_id, titulo: original.titulo, fecha_realizacion: original.fecha_realizacion, resumen: original.resumen, actividades: original.actividades, resultados: original.resultados, observaciones: original.observaciones, vinculos_ids: previousLinks.map((item) => item.id) };
    const changed = diffInforme(before, payload);
    return Object.keys(changed).length ? updateInforme(tipo, original.id, changed) : original;
  }, onSuccess: async (saved) => {
    await Promise.all([qc.invalidateQueries({ queryKey: ["informes", tipo] }), qc.invalidateQueries({ queryKey: ["informe", tipo, saved.id] }), qc.invalidateQueries({ queryKey: ["informe-historial", tipo, saved.id] }), qc.invalidateQueries({ queryKey: ["proyectos"] })]);
    navigate(editing ? `/informes/${tipo}/${saved.id}` : `/informes/${tipo}`, { replace: true, state: { successMessage: editing ? "¡Actualizado con éxito!" : "¡Creado con éxito!" } });
  }, onError: (reason) => {
    if (applyFieldErrors(reason, setErrors, ["memoria_id", "titulo", "fecha_realizacion", "resumen", "actividades", "resultados", "observaciones", "vinculos_ids"])) return;
    setError(getErrorMessage(reason, "Lo sentimos, no pudimos guardar los cambios. Verifique los datos e intente nuevamente."));
  } });

  if (!informeTipos.includes(rawTipo as InformeTipo)) return <p role="alert">Tipo de informe no disponible.</p>;
  if (editing && detail.isLoading) return <LoadingSkeleton variant="form" label="Cargando informe..." />;
  if (editing && (detail.isError || !detail.data)) return <p role="alert">Lo sentimos, no pudimos recuperar la información. <button type="button" className="underline" onClick={() => detail.refetch()}>Intente nuevamente</button>.</p>;
  const payload: InformePayload = { memoria_id: memoriaId, fecha_realizacion: toCivilDateString(date) ?? "", vinculos_ids: ids, ...text };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const next = validateInforme(payload, tipo);
    setErrors(next);
    if (Object.keys(next).length) { focusFieldErrors(next); return; }
    if (editing && detail.data) {
      const before: InformePayload = { memoria_id: detail.data.memoria_id, titulo: detail.data.titulo, fecha_realizacion: detail.data.fecha_realizacion, resumen: detail.data.resumen, actividades: detail.data.actividades, resultados: detail.data.resultados, observaciones: detail.data.observaciones, vinculos_ids: previousLinks.map((item) => item.id) };
      if (!Object.keys(diffInforme(before, payload)).length) {
        navigate(`/informes/${tipo}/${detail.data.id}`, { replace: true, state: { successMessage: "No había cambios para guardar." } });
        return;
      }
    }
    try { await mutation.mutateAsync(payload); } catch { /* El mensaje se muestra en onError. */ }
  };

  return <section className="w-full"><h1 className="text-2xl font-semibold leading-none md:text-3xl">{editing ? "Editar" : "Nuevo"} informe de {informeTipoLabel[tipo]}</h1>
    <form noValidate onSubmit={submit} className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6">
      <Field required label="Período de Memoria" name="memoria_id" error={errors.memoria_id}><select id="memoria_id" className="w-full rounded-lg border border-slate-300 p-3" value={memoriaId} disabled={editing || memorias.isLoading} onChange={(event) => { setMemoriaId(Number(event.target.value)); setChoicePage(1); if (memoriaId !== 0) { setIds([]); setSelectedNames({}); } }}><option value={0}>Seleccione un período</option>{(memorias.data ?? []).filter((item) => item.grupo_utn_id && !item.deleted_at).map((item) => <option key={item.id} value={item.id}>{formatFecha(item.periodo_inicio)} a {formatFecha(item.periodo_fin)}</option>)}</select></Field>
      {memorias.isError && <p role="alert" className="text-sm text-rose-700">Lo sentimos, no pudimos recuperar los períodos. <button type="button" onClick={() => memorias.refetch()} className="underline">Intente nuevamente</button>.</p>}
      <Field required label="Título" name="titulo" error={errors.titulo}><input id="titulo" className="w-full rounded-lg border border-slate-300 p-3" maxLength={200} placeholder="Título del informe" value={text.titulo} onChange={(event) => setText({ ...text, titulo: event.target.value })} /></Field>
      <Field required label="Fecha de realización" name="fecha_realizacion" error={errors.fecha_realizacion}><Calendar value={date} maxDate={new Date()} onChange={setDate} /></Field>
      {sections.map((field) => <Field key={field} required label={field[0].toUpperCase() + field.slice(1)} name={field} error={errors[field]}><textarea id={field} className="min-h-32 w-full rounded-lg border border-slate-300 p-3" maxLength={20000} placeholder={`Describa ${field}`} value={text[field]} onChange={(event) => setText({ ...text, [field]: event.target.value })} /></Field>)}
      {tipo !== "uct" && <fieldset className="space-y-3 rounded-xl border border-slate-200 p-4">
        <legend className="px-2 text-sm font-medium text-slate-800">{tipo === "pid" ? "Proyectos" : "Investigadores"} vinculados <span className="text-rose-500">*</span></legend>
        <p className="text-sm text-slate-600">Las vinculaciones se guardan juntas y sus datos quedan copiados en el informe.</p>
        {ids.length > 0 && <div aria-label="Registros seleccionados" className="flex flex-wrap gap-2">{ids.map((selectedId) => <button key={selectedId} type="button" onClick={() => setIds((current) => current.filter((item) => item !== selectedId))} className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-sm hover:bg-slate-100" aria-label={`Quitar ${selectedNames[selectedId] ?? `registro ${selectedId}`}`}>{selectedNames[selectedId] ?? `Registro ${selectedId}`} ×</button>)}</div>}
        <input aria-label={tipo === "investigadores" ? "Buscar investigadores para vincular" : "Buscar proyectos para vincular"} value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === "ArrowDown" && candidates.data?.data.length) { event.preventDefault(); candidateInputs.current[candidates.data.data[0].id]?.focus(); } }} placeholder={tipo === "investigadores" ? "Buscar por nombre" : "Buscar por nombre o código"} className="w-full rounded-lg border border-slate-300 p-3" disabled={!memoriaId} />
        {!memoriaId && <p className="text-sm text-slate-600">Seleccione primero un período.</p>}
        {candidates.isLoading && memoriaId > 0 && <p role="status">Cargando registros...</p>}
        {candidates.isError && <p role="alert" className="text-rose-700">Lo sentimos, no pudimos recuperar los registros. <button type="button" onClick={() => candidates.refetch()} className="underline">Intente nuevamente</button>.</p>}
        {candidates.data && <div className="max-h-60 space-y-2 overflow-y-auto">{candidates.data.data.length === 0 ? <p className="text-sm text-slate-600">No hay registros para esta búsqueda.</p> : candidates.data.data.map((item, index, items) => <label key={item.id} className="flex items-start gap-3 rounded-lg border border-slate-200 p-3 text-sm focus-within:border-slate-500 focus-within:ring-2 focus-within:ring-slate-200"><input type="checkbox" ref={(node) => { candidateInputs.current[item.id] = node; }} checked={ids.includes(item.id)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); event.currentTarget.click(); } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) { event.preventDefault(); const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : Math.max(0, Math.min(items.length - 1, index + (event.key === "ArrowDown" ? 1 : -1))); candidateInputs.current[items[next].id]?.focus(); } }} onChange={(event) => { setIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id)); if (event.target.checked) setSelectedNames((current) => ({ ...current, [item.id]: item.name })); }} /><span>{item.name}{!item.activo ? " (inactivo)" : ""}</span></label>)}</div>}
        {candidates.data && candidates.data.meta.total_pages > 1 && <nav aria-label="Páginas de registros" className="flex items-center justify-end gap-2"><Button size="sm" variant="secondary" disabled={choicePage <= 1} onClick={() => setChoicePage(choicePage - 1)}>Anterior</Button><span className="text-sm">Página {choicePage} de {candidates.data.meta.total_pages}</span><Button size="sm" variant="secondary" disabled={choicePage >= candidates.data.meta.total_pages} onClick={() => setChoicePage(choicePage + 1)}>Siguiente</Button></nav>}
        {errors.vinculos_ids && <p role="alert" className="text-sm text-rose-700">{errors.vinculos_ids}</p>}
      </fieldset>}
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      <div className="flex justify-between gap-3 pt-6"><Button variant="secondary" size="sm" onClick={() => navigate(editing ? `/informes/${tipo}/${id}` : `/informes/${tipo}`)}>Volver</Button><Button type="submit" size="sm" loading={mutation.isPending} loadingText="Guardando...">{editing ? "Actualizar" : "Guardar"}</Button></div>
    </form>
  </section>;
}
