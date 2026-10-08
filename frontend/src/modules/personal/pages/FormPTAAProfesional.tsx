import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { hasOnlyLettersAndSpaces } from "../../../lib/textValidation";
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
  initialData?: PersonalCompleto;
  onCancel: () => void;
  onError: (error: unknown) => void;
}

export default function FormPTAAProfesional({
  initialData,
  onCancel,
  onError,
}: Props) {
  const navigate = useNavigate();
  const { uct } = useUct();
  const { data: tiposPersonal = [], isLoading: tiposLoading, isFetching: tiposFetching, isError: tiposError, refetch: refetchTipos } = useTiposPersonal();
  const qc = useQueryClient();
  const isEdit = Boolean(initialData);
  const { user } = useAuth();

  const [nombreApellido, setNombre] = useState("");
  const [dni, setDni] = useState("");
  const [cuil, setCuil] = useState("");
  const [horasSemanales, setHoras] = useState<number | "">("");
  const [tipoPersonalId, setTipoPersonalId] = useState<number | "">("");
  const [fechaAltaGrupo, setFechaAltaGrupo] = useState<Date | null>(null);
  const [activo, setActivo] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [hydrated, setHydrated] = useState(!isEdit);

  useEffect(() => {
    if (!initialData) {
      setNombre("");
      setDni("");
      setCuil("");
      setHoras("");
      setTipoPersonalId("");
      setFechaAltaGrupo(null);
      setActivo(true);
      return;
    }

    setNombre(initialData.nombre_apellido ?? "");
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
    module: "personal-personal",
    recordId: initialData?.id,
    value: { nombreApellido, dni, cuil, horasSemanales, tipoPersonalId, fechaAltaGrupo: toCivilDateString(fechaAltaGrupo), activo },
    ready: hydrated,
    autosave: false,
    hasContent: (draft) => Boolean(draft.nombreApellido || draft.dni || draft.cuil || draft.horasSemanales || draft.tipoPersonalId || draft.fechaAltaGrupo),
    onRestore: (draft) => {
      setNombre(draft.nombreApellido); setDni(draft.dni ?? ""); setCuil(draft.cuil ?? ""); setHoras(draft.horasSemanales); setTipoPersonalId(draft.tipoPersonalId);
      setFechaAltaGrupo(draft.fechaAltaGrupo ? new Date(`${draft.fechaAltaGrupo}T00:00:00`) : null); setActivo(draft.activo);
    },
  });

  const hasUnsavedChanges = () => {
    if (!initialData) return true;
    return nombreApellido !== (initialData.nombre_apellido ?? "") ||
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

    if (!nombreApellido.trim()) {
      newErrors.nombre = "Debe ingresar nombre y apellido";
    } else if (!hasOnlyLettersAndSpaces(nombreApellido)) {
      newErrors.nombre = "Use solo letras y espacios en nombre y apellido";
    }

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
      if (applyFieldErrors(error, setErrors, ["nombre","dni","cuil","horas","tipoPersonal","fechaAltaGrupo","grupo"])) return false;
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
        nombre_apellido: nombreApellido,
        dni,
        cuil,
        horas_semanales: Number(horasSemanales),
        tipo_personal_id: Number(tipoPersonalId),
        fecha_alta_grupo: formatDateStr(fechaAltaGrupo),
        grupo_utn_id: uct!.id,
        activo,
      };

      if (isEdit && initialData?.id) {
        const original = {
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

      <Field label="Nombre y apellido" required error={errors.nombre} name="nombre">
        <input
          id="personal-nombre"
          aria-label="Nombre y apellido"
          placeholder="Ingrese nombre y apellido"
          className={`input ${
            errors.nombre ? "border-red-500 ring-2 ring-red-500" : ""
          }`}
          value={nombreApellido}
          aria-invalid={Boolean(errors.nombre)}
          onChange={(e) => {
            setNombre(e.target.value);
            if (e.target.value.trim()) clearError("nombre");
          }}
        />
      </Field>

      <IdentidadFields prefix="personal" dni={dni} cuil={cuil} errors={errors}
        onDniChange={(value) => { setDni(value); clearError("dni"); clearError("cuil"); }}
        onCuilChange={(value) => { setCuil(value); clearError("cuil"); }} />

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
          aria-invalid={Boolean(errors.horas)}
          onChange={(e) => {
            const value = e.target.value === "" ? "" : +e.target.value;
            setHoras(value);
            if (validWeeklyHours(value)) clearError("horas");
          }}
        />
      </Field>

      <div id="personal-fechaAltaGrupo" tabIndex={-1}>
      <Field label="Fecha de alta en el grupo" required error={errors.fechaAltaGrupo} name="fechaAltaGrupo">
        <Calendar
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
        <Field label="Función del personal" required error={errors.tipoPersonal} name="tipoPersonal">
          <select
            id="personal-tipoPersonal"
            aria-label="Función del personal"
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
