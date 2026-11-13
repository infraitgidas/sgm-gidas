import type { ReclasificarFormulario } from "@/modules/personal/services/reclasificacionService";
import NombrePersonalFields from "@/modules/personal/components/NombrePersonalFields";
import { validatePersonalName, validatePersonalStartDate, updatePersonalErrors } from "@/modules/personal/utils/personalValidation";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { LoaderCircle } from "lucide-react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Button from "@/components/Button";
import Calendar from "@/components/Calendar";
import Field from "@/components/Field";
import { useUct } from "@/modules/grupo/hooks/useUct";
import { useTiposPersonal } from "@/modules/personal/hooks/useTiposPersonal";
import {
  upsertPersonal,
  actualizarPersonal,
} from "@/modules/personal/services/personalServices";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import { toCivilDateString } from "@/utils/dateTime";
import type { PersonalCompleto } from "@/modules/personal/services/personalCompletoServices";
import { personalFieldErrors } from "@/modules/personal/utils/personalFieldErrors";
import { validateDni, validateCuil } from "@/modules/personal/utils/identidadValidation";
import IdentidadFields from "@/modules/personal/components/IdentidadFields";
import { MAX_HORAS_SEMANALES, validWeeklyHours, WEEKLY_HOURS_ERROR } from "@/modules/personal/utils/weeklyHours";

interface Props {
  onReclassify?: ReclasificarFormulario;
  onSavingChange?: (saving: boolean) => void;
  initialData?: PersonalCompleto;
  onCancel: () => void;
  onError: (error: unknown) => void;
}

export default function FormPTAAProfesional({
  initialData,
  onReclassify,
  onSavingChange,
  onCancel,
  onError,
}: Props) {
  const navigate = useNavigate();
  const { uct } = useUct();
  const { data: catalogoPersonal = [], isLoading: tiposLoading, isFetching: tiposFetching, isError: tiposError, refetch: refetchTipos } = useTiposPersonal();
  const tiposPersonal = catalogoPersonal.filter((tipo) => tipo.compatible_con_personal !== false);
  const qc = useQueryClient();
  const isEdit = Boolean(initialData);
  const { user } = useAuth();

  const [nombreApellido, setNombre] = useState("");
  const [apellido, setApellido] = useState("");
  const [dni, setDni] = useState("");
  const [cuil, setCuil] = useState("");
  const [horasSemanales, setHoras] = useState<number | "">("");
  const [tipoPersonalId, setTipoPersonalId] = useState<number | "">("");
  const [fechaAltaGrupo, setFechaAltaGrupo] = useState<Date | null>(null);
  const [activo, setActivo] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  useEffect(() => { onSavingChange?.(isSaving); }, [isSaving, onSavingChange]);
  const [hydrated, setHydrated] = useState(!isEdit);

  useEffect(() => {
    if (!initialData) {
      setNombre("");
      setApellido("");
      setDni("");
      setCuil("");
      setHoras("");
      setTipoPersonalId("");
      setFechaAltaGrupo(null);
      setActivo(true);
      return;
    }

    setNombre(initialData.nombre ?? "");
    setApellido(initialData.apellido ?? "");
    setDni(initialData.dni ?? "");
    setCuil(initialData.cuil ?? "");
    setHoras(initialData.horas_semanales ?? "");
    setActivo(initialData.activo ?? true);
    setFechaAltaGrupo(
      initialData.fecha_alta_grupo
        ? new Date(`${initialData.fecha_alta_grupo}T00:00:00`)
        : null
    );
    setTipoPersonalId(
      initialData.relaciones?.tipo_personal?.id ??
        initialData.tipo_personal_id ??
        ""
    );
    setHydrated(true);
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: onReclassify ? `personal-reclasificar-${initialData?.rol}-personal` : "personal-personal",
    recordId: initialData?.id,
    value: { nombreApellido, apellido, dni, cuil, horasSemanales, tipoPersonalId, fechaAltaGrupo: toCivilDateString(fechaAltaGrupo), activo },
    ready: hydrated,
    autosave: false,
    hasContent: (draft) => Boolean(draft.nombreApellido || draft.apellido || draft.dni || draft.cuil || draft.horasSemanales || draft.tipoPersonalId || draft.fechaAltaGrupo),
    onRestore: (draft) => {
      setNombre(draft.nombreApellido); setApellido(draft.apellido ?? ""); setDni(draft.dni ?? ""); setCuil(draft.cuil ?? ""); setHoras(draft.horasSemanales); setTipoPersonalId(draft.tipoPersonalId);
      setFechaAltaGrupo(draft.fechaAltaGrupo ? new Date(`${draft.fechaAltaGrupo}T00:00:00`) : null); setActivo(draft.activo);
    },
  });

  const hasUnsavedChanges = () => {
    if (!initialData) return true;
    return nombreApellido !== (initialData.nombre ?? "") ||
      apellido !== (initialData.apellido ?? "") ||
      dni !== (initialData.dni ?? "") || cuil !== (initialData.cuil ?? "") ||
      Number(horasSemanales) !== Number(initialData.horas_semanales) ||
      Number(tipoPersonalId) !== Number(initialData.relaciones?.tipo_personal?.id ?? initialData.tipo_personal_id) ||
      toCivilDateString(fechaAltaGrupo) !== (initialData.fecha_alta_grupo ?? "") ||
      activo !== (initialData.activo ?? true);
  };

  const handleCancel = () => {
    if (isEdit && !availableDraft && !hasUnsavedChanges()) {
      clearDraft();
      onCancel();
      return;
    }
    requestLeave(onCancel);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    Object.assign(newErrors, validatePersonalName(nombreApellido, apellido));

    const dniError = validateDni(dni);
    if (dniError) newErrors.dni = dniError;
    const cuilError = validateCuil(cuil, dni);
    if (cuilError) newErrors.cuil = cuilError;

    if (!validWeeklyHours(horasSemanales)) {
      newErrors.horas = WEEKLY_HOURS_ERROR;
    }

    if (!tipoPersonalId || !tiposPersonal.some((t) => t.id === tipoPersonalId)) {
      newErrors.tipoPersonal = "Debe seleccionar tipo de personal";
    }

    if (!fechaAltaGrupo) {
      newErrors.fechaAltaGrupo = "Debe ingresar la fecha de alta en el grupo";
    }

    if (!uct?.id) {
      newErrors.grupo = "Lo sentimos, no pudimos recuperar el grupo. Intente nuevamente.";
    }
    const dateError = validatePersonalStartDate(fechaAltaGrupo);
    if (dateError) newErrors.fechaAltaGrupo = dateError;
    setErrors(newErrors);
    if (Object.keys(newErrors).length) {
      focusFieldErrors(newErrors);
      onError(new Error("No pudimos guardar el registro. Complete o corrija los campos indicados e intente nuevamente."));
    }
    return Object.keys(newErrors).length === 0;
  };

  const clearError = (field: string) => {
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  const formatDateStr = (d: Date | null) => {
    if (!d) return "";
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${dd}`;
  };

  const executeSafely = async (operation: () => Promise<unknown>) => {
    try {
      await operation();
      return true;
    } catch (error) {
      onError(error);
      if (applyFieldErrors(error, setErrors, ["nombre","apellido","dni","cuil","horas","tipoPersonal","fechaAltaGrupo","grupo"])) return false;
      const fieldErrors = personalFieldErrors(error);
      if (Object.keys(fieldErrors).length) {
        setErrors(fieldErrors);
        requestAnimationFrame(() => {
          document.getElementById(`personal-${Object.keys(fieldErrors)[0]}`)?.focus();
        });
      }
      return false;
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSaving) return;
    if (!validate()) return;
    setIsSaving(true);
    try {

      const payload = {
        nombre: nombreApellido.trim(),
        apellido: apellido.trim(),
        nombre_apellido: `${nombreApellido.trim()} ${apellido.trim()}`,
        dni,
        cuil,
        horas_semanales: Number(horasSemanales),
        tipo_personal_id: Number(tipoPersonalId),
        fecha_alta_grupo: formatDateStr(fechaAltaGrupo),
        grupo_utn_id: uct!.id,
        activo,
      };

      if (onReclassify) {
        let result: PersonalCompleto | undefined;
        const saved = await executeSafely(async () => { result = await onReclassify(payload); });
        if (saved && result) {
          clearDraft();
          navigate(`/personal/${result.rol}/${result.id}`, { replace: true, state: { successMessage: "¡Actualizado con éxito!" } });
        }
        return;
      }

      if (isEdit && initialData?.id) {
        const original = {
          nombre: initialData.nombre ?? undefined,
          apellido: initialData.apellido ?? undefined,
          nombre_apellido: initialData.nombre_apellido,
          dni: initialData.dni ?? "",
          cuil: initialData.cuil ?? "",
          horas_semanales: Number(initialData.horas_semanales),
          tipo_personal_id: Number(initialData.relaciones?.tipo_personal?.id ?? initialData.tipo_personal_id),
          fecha_alta_grupo: initialData.fecha_alta_grupo,
          grupo_utn_id: Number(initialData.grupo_utn_id ?? uct!.id),
          activo: initialData.activo ?? true,
        };
        const changedPayload = Object.fromEntries(
          Object.entries(payload).filter(
            ([key, value]) => value !== original[key as keyof typeof original]
          )
        );
        if (Object.keys(changedPayload).length > 0) {
          const updated = await executeSafely(() =>
            actualizarPersonal(
              initialData.id,
              changedPayload,
              "personal"
            )
          );
          if (!updated) return;
        }

        await qc.invalidateQueries({
          queryKey: ["personal"],
        });

        clearDraft();
        navigate(
          `/personal/personal/${initialData.id}`,
          {
            replace: true,
            state: { successMessage: "¡Actualizado con éxito!" },
          }
        );

        return;
      }

      const created = await executeSafely(() => upsertPersonal(payload));
      if (!created) return;

      await qc.invalidateQueries({
        queryKey: ["personal"],
      });

      clearDraft();
      navigate("/personal", {
        state: { successMessage: "¡Creado con éxito!" },
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
    >
      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      {errors.grupo && <p id="personal-grupo" tabIndex={-1} role="alert">{errors.grupo}</p>}

      <NombrePersonalFields prefix="personal" nombre={nombreApellido} apellido={apellido}
        errors={errors} onNombreChange={(value) => {
          setNombre(value);
          const next = validatePersonalName(value, apellido);
          setErrors((prev) => updatePersonalErrors(prev, { nombre: next.nombre, ...(apellido || prev.apellido ? { apellido: next.apellido } : {}) }));
        }}
        onApellidoChange={(value) => {
          setApellido(value);
          const next = validatePersonalName(nombreApellido, value);
          setErrors((prev) => updatePersonalErrors(prev, { apellido: next.apellido }));
        }} />

      <IdentidadFields prefix="personal" dni={dni} cuil={cuil} errors={errors}
        onDniChange={(value) => {
          setDni(value);
          setErrors((prev) => updatePersonalErrors(prev, { dni: validateDni(value), ...(cuil || prev.cuil ? { cuil: validateCuil(cuil, value) } : {}) }));
        }}
        onCuilChange={(value) => {
          setCuil(value);
          setErrors((prev) => updatePersonalErrors(prev, { cuil: validateCuil(value, dni) }));
        }} />

      <Field label="Horas semanales" required error={errors.horas} name="horas">
        <input
          id="personal-horas"
          aria-label="Horas semanales"
          placeholder="Ingrese horas semanales"
          type="number"
          min="1"
          max={MAX_HORAS_SEMANALES}
          step="1"
          className={`input ${
            errors.horas ? "border-red-500 ring-2 ring-red-500" : ""
          }`}
          value={horasSemanales}
          onBlur={() => setErrors((prev) => updatePersonalErrors(prev, { horas: validWeeklyHours(horasSemanales) ? null : WEEKLY_HOURS_ERROR }))}
          aria-invalid={Boolean(errors.horas)}
          onChange={(e) => {
            const value = e.target.value === "" ? "" : +e.target.value;
            setHoras(value);
            setErrors((prev) => updatePersonalErrors(prev, { horas: validWeeklyHours(value) ? null : WEEKLY_HOURS_ERROR }));
          }}
        />
      </Field>

      <div id="personal-fechaAltaGrupo" tabIndex={-1}>
      <Field label="Fecha de alta en el grupo" required error={errors.fechaAltaGrupo} name="fechaAltaGrupo">
        <Calendar
          maxDate={new Date()}
          value={fechaAltaGrupo}
          onChange={(date) => {
            setFechaAltaGrupo(date);
            if (date) clearError("fechaAltaGrupo");
          }}
          className={`input ${
            errors.fechaAltaGrupo ? "border-red-500 ring-2 ring-red-500" : ""
          }`}
          helperText={errors.fechaAltaGrupo ? undefined : "DD/MM/AAAA"}
        />
      </Field>
      </div>

      <div>
        {tiposLoading && <LoadingSkeleton variant="compact" label="Cargando tipos de personal…" />}
        {tiposError && <div role="alert">
          <p>Lo sentimos, no pudimos recuperar los tipos de personal. Intente nuevamente.</p>
          <Button type="button" variant="secondary" onClick={() => void refetchTipos()} loading={tiposFetching} loadingText="Reintentando...">Reintentar</Button>
        </div>}
        {!tiposLoading && !tiposError && !tiposPersonal.length && <p role="alert">No hay tipos de personal disponibles. Agregue un tipo en el catálogo e intente nuevamente.</p>}
        {!tiposLoading && !tiposError && isEdit && tipoPersonalId && !tiposPersonal.some((tipo) => tipo.id === tipoPersonalId) && (
          <p role="status" className="text-sm text-slate-600">El tipo asignado actualmente ya no está disponible. Seleccione un tipo vigente para guardar cambios.</p>
        )}
        <Field label="Tipo de Personal" required error={errors.tipoPersonal} name="tipoPersonal">
          <select
            id="personal-tipoPersonal"
            aria-label="Tipo de Personal"
            className={`input ${
              errors.tipoPersonal ? "border-red-500 ring-2 ring-red-500" : ""
            }`}
            value={tipoPersonalId}
            disabled={tiposLoading || tiposError || !tiposPersonal.length}
            aria-invalid={Boolean(errors.tipoPersonal)}
            onChange={(e) => {
              const value = e.target.value ? +e.target.value : "";
              setTipoPersonalId(value);
              if (value) clearError("tipoPersonal");
            }}
          >
            <option value="" disabled>
              Seleccionar tipo de personal
            </option>
            {isEdit && tipoPersonalId && !tiposPersonal.some((t) => t.id === tipoPersonalId) && (
              <option value={tipoPersonalId} disabled>{initialData?.relaciones?.tipo_personal?.nombre ?? "Tipo actual"} (no disponible)</option>
            )}
            {tiposPersonal.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="flex justify-between pt-6">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleCancel}
        >
          Volver
        </Button>

        <Button type="submit" size="sm" disabled={isSaving} aria-busy={isSaving} loading={isSaving} loadingText="Guardando...">
          {isSaving && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />}
          {isSaving ? "Guardando..." : isEdit ? "Actualizar" : "Guardar"}
        </Button>
      </div>
    <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />
    </form>
  );
}
