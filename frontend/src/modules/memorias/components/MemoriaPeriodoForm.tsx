import { getGruposUtn } from "@/modules/grupo/services/gruposUtnServices";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import Field from "@/components/Field";
import DatePicker from "@/components/Calendar";
import { getErrorMessage, applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { toCivilDateString } from "@/utils/dateTime";
import { updateMemoria, type Memoria, type MemoriaPayload } from "@/modules/memorias/services/memoriasService";

export default function MemoriaPeriodoForm({ memoria, onCancel, onSaved }: {
  memoria: Memoria; onCancel: () => void; onSaved: () => void;
}) {
  const [grupoId, setGrupoId] = useState(memoria.grupo_utn_id ? String(memoria.grupo_utn_id) : "");
  const { data: grupos = [] } = useQuery({ queryKey: ["grupos-utn"], queryFn: getGruposUtn, enabled: memoria.grupo_utn_id === null });
  const [inicio, setInicio] = useState(memoria.periodo_inicio);
  const [fin, setFin] = useState(memoria.periodo_fin);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const qc = useQueryClient();
  const { mutateAsync, isPending } = useMutation({
    mutationFn: (payload: Partial<Pick<MemoriaPayload, "periodo_inicio" | "periodo_fin" | "grupo_utn_id">>) => updateMemoria(memoria.id, payload),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["memorias"] });
      await qc.invalidateQueries({ queryKey: ["memoria"] });
      await qc.invalidateQueries({ queryKey: ["memoria-historial", String(memoria.id)] });
      onSaved();
    },
    onError: (error: unknown) => {
      if (applyFieldErrors(error, setErrors, ["grupo_utn_id", "periodo_inicio", "periodo_fin"])) return;
      setError(getErrorMessage(error, "Lo sentimos, no pudimos actualizar el período de la memoria. Revise las fechas e intente nuevamente."));
    },
  });
  return <form noValidate className="space-y-4" onSubmit={async (event) => {
    event.preventDefault();
    if (isPending) return;
    const next: Record<string, string> = {};
    if (!grupoId) next.grupo_utn_id = "Debe seleccionar una UCT.";
    if (!inicio) next.periodo_inicio = "Debe ingresar el inicio del período.";
    if (!fin) next.periodo_fin = "Debe ingresar el fin del período.";
    if (inicio && fin && fin < inicio) next.periodo_fin = "El fin no puede ser anterior al inicio.";
    setErrors(next); setError("");
    if (Object.keys(next).length) { focusFieldErrors(next); return; }
    const payload: Partial<Pick<MemoriaPayload, "periodo_inicio" | "periodo_fin" | "grupo_utn_id">> = {};
    if (memoria.grupo_utn_id === null) payload.grupo_utn_id = Number(grupoId);
    if (inicio !== memoria.periodo_inicio) payload.periodo_inicio = inicio;
    if (fin !== memoria.periodo_fin) payload.periodo_fin = fin;
    if (!Object.keys(payload).length) { onCancel(); return; }
    try { await mutateAsync(payload); } catch { /* onError muestra el mensaje */ }
  }}>
    <p className="text-sm text-slate-500">Puede corregir el período hasta que exista una versión cerrada. Las fechas de apertura y cierre no cambian.</p>
    <fieldset disabled={isPending} className="space-y-4">
      {memoria.grupo_utn_id === null && <Field required label="UCT" name="grupo_utn_id" error={errors.grupo_utn_id}>
        <select id="grupo_utn_id" value={grupoId} onChange={(event) => setGrupoId(event.target.value)} className="w-full rounded-lg border border-slate-200 p-3">
          <option value="">Seleccione la UCT de esta memoria</option>
          {grupos.map((grupo) => <option key={grupo.id} value={grupo.id}>{grupo.nombre}</option>)}
        </select>
      </Field>}
      <Field required label="Inicio del período" name="periodo_inicio" error={errors.periodo_inicio}>
        <DatePicker value={inicio ? new Date(`${inicio}T00:00:00`) : null} onChange={(date) => {
          setInicio(toCivilDateString(date) ?? ""); setErrors((prev) => ({ ...prev, periodo_inicio: "" }));
        }} helperText="DD/MM/AAAA" />
      </Field>
      <Field required label="Fin del período" name="periodo_fin" error={errors.periodo_fin}>
        <DatePicker value={fin ? new Date(`${fin}T00:00:00`) : null} onChange={(date) => {
          setFin(toCivilDateString(date) ?? ""); setErrors((prev) => ({ ...prev, periodo_fin: "" }));
        }} helperText="DD/MM/AAAA" />
      </Field>
    </fieldset>
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    <div className="flex flex-wrap gap-2">
      <Button type="submit" size="sm" loading={isPending} loadingText="Guardando...">Guardar</Button>
      <Button type="button" size="sm" variant="secondary" disabled={isPending} onClick={onCancel}>Cancelar</Button>
    </div>
  </form>;
}
