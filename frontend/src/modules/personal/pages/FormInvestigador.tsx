import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { hasOnlyLettersAndSpaces } from "../../../lib/textValidation";
import { LoaderCircle } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import { toCivilDateString } from "@/utils/dateTime";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Button from "@/components/Button";
import Field from "@/components/Field";
import Calendar from "@/components/Calendar";
import { useUct } from "@/modules/grupo/hooks/useUct";
import { useDedicaciones } from "@/modules/personal/hooks/useDedicaciones";
import { useCategoriasUtn } from "@/modules/catalogos/hooks/useCategoriasUtn";
import { useProgramasIncentivos } from "@/modules/grupo/hooks/useProgramasIncentivos";
import {
  crearInvestigador,
  actualizarInvestigador,
} from "@/modules/personal/services/investigadorServices";
import type { PersonalCompleto } from "@/modules/personal/services/personalCompletoServices";
import { MAX_HORAS_SEMANALES, validWeeklyHours, WEEKLY_HOURS_ERROR } from "@/modules/personal/utils/weeklyHours";
import { personalFieldErrors } from "@/modules/personal/utils/personalFieldErrors";
import { validateDni, validateCuil } from "@/modules/personal/utils/identidadValidation";
import IdentidadFields from "@/modules/personal/components/IdentidadFields";

interface Props {
  initialData?: PersonalCompleto;
  onCancel: () => void;
  onError: (error: unknown) => void;
}

export default function FormInvestigador({
  initialData,
  onCancel,
  onError,
}: Props) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { uct } = useUct();
  const { data: dedicaciones = [] } = useDedicaciones();
  const { data: categorias = [] } = useCategoriasUtn();
  const { data: programas = [] } = useProgramasIncentivos();

  const isEdit = Boolean(initialData);
  const { user } = useAuth();

  const [nombreApellido, setNombre] = useState("");
  const [dni, setDni] = useState("");
  const [cuil, setCuil] = useState("");
  const [horasSemanales, setHoras] = useState<number | "">("");
  const [dedicacionId, setDedicacionId] = useState<number | "">("");
  const [categoriaId, setCategoriaId] = useState<number | null>(null);
  const [programaId, setProgramaId] = useState<number | null>(null);
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
      setDedicacionId("");
      setCategoriaId(null);
      setProgramaId(null);
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
    setDedicacionId(
      initialData.relaciones?.tipo_dedicacion?.id ??
        initialData.tipo_dedicacion_id ??
        ""
    );
    setCategoriaId(
      initialData.relaciones?.categoria_utn?.id ??
        initialData.categoria_utn_id ??
        null
    );
    setProgramaId(
      initialData.relaciones?.programa_incentivos?.id ??
        initialData.programa_incentivos_id ??
        null
    );
    setHydrated(true);
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "personal-investigador",
    recordId: initialData?.id,
    value: { nombreApellido, dni, cuil, horasSemanales, dedicacionId, categoriaId, programaId, fechaAltaGrupo: toCivilDateString(fechaAltaGrupo), activo },
    ready: hydrated,
    autosave: false,
    hasContent: (draft) => Boolean(draft.nombreApellido || draft.dni || draft.cuil || draft.horasSemanales || draft.dedicacionId || draft.categoriaId || draft.programaId || draft.fechaAltaGrupo),
    onRestore: (draft) => {
      setNombre(draft.nombreApellido); setDni(draft.dni ?? ""); setCuil(draft.cuil ?? ""); setHoras(draft.horasSemanales); setDedicacionId(draft.dedicacionId);
      setCategoriaId(draft.categoriaId); setProgramaId(draft.programaId);
      setFechaAltaGrupo(draft.fechaAltaGrupo ? new Date(`${draft.fechaAltaGrupo}T00:00:00`) : null); setActivo(draft.activo);
    },
  });

  const hasUnsavedChanges = () => {
    if (!initialData) return true;
    return nombreApellido !== (initialData.nombre_apellido ?? "") ||
      dni !== (initialData.dni ?? "") || cuil !== (initialData.cuil ?? "") ||
      Number(horasSemanales) !== Number(initialData.horas_semanales) ||
      Number(dedicacionId) !== Number(initialData.relaciones?.tipo_dedicacion?.id ?? initialData.tipo_dedicacion_id) ||
      categoriaId !== (initialData.relaciones?.categoria_utn?.id ?? initialData.categoria_utn_id ?? null) ||
      programaId !== (initialData.relaciones?.programa_incentivos?.id ?? initialData.programa_incentivos_id ?? null) ||
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

    if (!dedicacionId) {
      newErrors.dedicacion = "Debe seleccionar dedicación";
    }

    if (!fechaAltaGrupo) {
      newErrors.fechaAltaGrupo = "Debe ingresar la fecha de alta en el grupo";
    }
    if (!uct?.id) newErrors.grupo = "Lo sentimos, no pudimos recuperar el grupo. Intente nuevamente.";

    setErrors(newErrors);
    if (Object.keys(newErrors).length) {
      focusFieldErrors(newErrors);
      onError(new Error("No pudimos guardar el registro. Complete o corrija los campos indicados e intente nuevamente."));
    }
    return Object.keys(newErrors).length === 0;
  };

  const executeSafely = async (operation: () => Promise<unknown>) => {
    try {
      await operation();
      return true;
    } catch (error) {
      onError(error);
      if (applyFieldErrors(error, setErrors, ["nombre","dni","cuil","horas","dedicacion","categoria","programa","fechaAltaGrupo"])) return false;
      const fieldErrors = personalFieldErrors(error);
      if (fieldErrors.horas) {
        setErrors((prev) => ({ ...prev, horas: fieldErrors.horas }));
        document.getElementById("investigador-horas")?.focus();
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
        tipo_dedicacion_id: Number(dedicacionId),
        categoria_utn_id: categoriaId,
        programa_incentivos_id: programaId,
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
          tipo_dedicacion_id: Number(initialData.relaciones?.tipo_dedicacion?.id ?? initialData.tipo_dedicacion_id),
          categoria_utn_id: initialData.relaciones?.categoria_utn?.id ?? initialData.categoria_utn_id ?? null,
          programa_incentivos_id: initialData.relaciones?.programa_incentivos?.id ?? initialData.programa_incentivos_id ?? null,
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
            actualizarInvestigador(initialData.id, changedPayload, "investigador")
          );
          if (!updated) return;
        }

        await Promise.all([
          qc.invalidateQueries({ queryKey: ["personal"] }),
          qc.invalidateQueries({ queryKey: ["investigadores"] }),
          qc.invalidateQueries({ queryKey: ["proyecto-candidatos"] }),
          qc.invalidateQueries({ queryKey: ["personal-edit", "investigador", String(initialData.id)] }),
          qc.invalidateQueries({ queryKey: ["personal-detalle", "investigador", String(initialData.id)] }),
        ]);
        clearDraft();
        navigate(`/personal/investigador/${initialData.id}`, {
          replace: true,
          state: { successMessage: "¡Actualizado con éxito!" },
        });

        return;
      }

      const created = await executeSafely(() => crearInvestigador(payload));
      if (!created) return;
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["personal"] }),
        qc.invalidateQueries({ queryKey: ["investigadores"] }),
        qc.invalidateQueries({ queryKey: ["proyecto-candidatos"] }),
      ]);

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
      noValidate
      onSubmit={submit}
      className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
    >
      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      {errors.grupo && <p role="alert">{errors.grupo}</p>}
      <Field required label="Nombre y apellido" name="nombre" error={errors.nombre}>
        <>
          <input
            className={`input ${
              errors.nombre ? "!border-red-500 !ring-2 !ring-red-500" : ""
            }`}
            value={nombreApellido}
            onChange={(e) => {
              setNombre(e.target.value);
              if (e.target.value.trim()) clearError("nombre");
            }}
          />
          {errors.nombre && (
            <p className="mt-1 text-sm text-red-500">{errors.nombre}</p>
          )}
        </>
      </Field>

      <IdentidadFields prefix="investigador" dni={dni} cuil={cuil} errors={errors}
        onDniChange={(value) => { setDni(value); clearError("dni"); clearError("cuil"); }}
        onCuilChange={(value) => { setCuil(value); clearError("cuil"); }} />

      <Field required label="Horas semanales" name="horas" error={errors.horas}>
        <>
          <input
            type="number"
            min="1"
            max={MAX_HORAS_SEMANALES}
            step="1"
            aria-label="Horas semanales"
            id="investigador-horas"
            aria-describedby={errors.horas ? "investigador-horas-error" : undefined}
            aria-invalid={Boolean(errors.horas)}
            className={`input ${
              errors.horas ? "!border-red-500 !ring-2 !ring-red-500" : ""
            }`}
            value={horasSemanales}
            onChange={(e) => {
              const value = e.target.value === "" ? "" : +e.target.value;
              setHoras(value);
              if (validWeeklyHours(value)) clearError("horas");
            }}
          />
          {errors.horas && (
            <p id="investigador-horas-error" role="alert" className="mt-1 text-sm text-red-500">{errors.horas}</p>
          )}
        </>
      </Field>

      <Field required label="Dedicacion" name="dedicacion" error={errors.dedicacion}>
        <>
          <select
            className={`input ${
              errors.dedicacion ? "!border-red-500 !ring-2 !ring-red-500" : ""
            } ${!dedicacionId ? "text-slate-400" : "text-slate-900"}`}
            value={dedicacionId}
            onChange={(e) => {
              const value = e.target.value ? +e.target.value : "";
              setDedicacionId(value);
              if (value) clearError("dedicacion");
            }}
          >
            <option value="" disabled>
              Seleccionar dedicación
            </option>
            {dedicaciones.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nombre}
              </option>
            ))}
          </select>
          {errors.dedicacion && (
            <p className="mt-1 text-sm text-red-500">{errors.dedicacion}</p>
          )}
        </>
      </Field>

      <Field label="Categoría UTN" name="categoria" error={errors.categoria}>
        <>
          <select
            className={`input ${
              errors.categoria ? "!border-red-500 !ring-2 !ring-red-500" : ""
            } ${!categoriaId ? "text-slate-400" : "text-slate-900"}`}
            value={categoriaId ?? ""}
            onChange={(e) => {
              const value = e.target.value ? +e.target.value : null;
              setCategoriaId(value);
              clearError("categoria");
            }}
          >
            <option value="">
              Sin categoría UTN
            </option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          {errors.categoria && (
            <p className="mt-1 text-sm text-red-500">{errors.categoria}</p>
          )}
        </>
      </Field>

      <Field label="Programa de incentivos" name="programa" error={errors.programa}>
        <>
          <select
            className={`input ${
              errors.programa ? "!border-red-500 !ring-2 !ring-red-500" : ""
            } ${!programaId ? "text-slate-400" : "text-slate-900"}`}
            value={programaId ?? ""}
            onChange={(e) => {
              const value = e.target.value ? +e.target.value : null;
              setProgramaId(value);
              clearError("programa");
            }}
          >
            <option value="">
              Sin programa de incentivos
            </option>
            {programas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
          {errors.programa && (
            <p className="mt-1 text-sm text-red-500">{errors.programa}</p>
          )}
        </>
      </Field>

      <Field required label="Fecha de alta en el grupo" name="fechaAltaGrupo" error={errors.fechaAltaGrupo}>
        <Calendar
          value={fechaAltaGrupo}
          onChange={(date) => {
            setFechaAltaGrupo(date);
            if (date) clearError("fechaAltaGrupo");
          }}
          className={`input ${
            errors.fechaAltaGrupo ? "!border-red-500 !ring-2 !ring-red-500" : ""
          }`}
          helperText="DD/MM/AAAA"
        />
      </Field>

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
