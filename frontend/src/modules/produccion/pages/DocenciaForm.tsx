import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors } from "@/lib/httpError";
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import Calendar from "@/components/Calendar";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";
import { getErrorMessage } from "@/lib/httpError";
import { useInvestigadores } from "@/modules/personal/hooks/useInvestigadores";
import { useGradosAcademicos } from "@/modules/produccion/hooks/useGradoAcademico";
import { useRolesActividadDocencia } from "@/modules/produccion/hooks/useActividadDocenciaRol";
import { toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import {
  crearActividadDocencia,
  getActividadDocenciaById,
  actualizarActividadDocencia,
  type ActividadDocenciaPayload,
} from "@/modules/produccion/services/actividadDocenciaServices";

export default function FormDocenciaInvestigador() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const isEdit = Boolean(id);

  const { data: investigadores = [] } = useInvestigadores();
  const { data: gradosAcademicos = [] } = useGradosAcademicos();
  const { data: rolesActividad = [] } = useRolesActividadDocencia();

  const { data: initialData, isLoading } = useQuery({
    queryKey: ["docencia", id],
    queryFn: () => (id ? getActividadDocenciaById(Number(id)) : null),
    enabled: isEdit,
  });

  const [investigadorId, setInvestigadorId] = useState<number | null>(null);
  const [curso, setCurso] = useState("");
  const [institucion, setInstitucion] = useState("");
  const [fechaInicio, setFechaInicio] = useState<Date | null>(null);
  const [fechaFin, setFechaFin] = useState<Date | null>(null);
  const [gradoAcademicoId, setGradoAcademicoId] = useState<number | null>(null);
  const [rolActividadId, setRolActividadId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!initialData) {
      setInvestigadorId(null);
      setCurso("");
      setInstitucion("");
      setFechaInicio(null);
      setFechaFin(null);
      setGradoAcademicoId(null);
      setRolActividadId(null);
      return;
    }

    setInvestigadorId(
      initialData.investigador_id ??
        (typeof initialData.investigador === "object"
          ? initialData.investigador?.id ?? null
          : null)
    );
    setCurso(initialData.curso ?? "");
    setInstitucion(initialData.institucion ?? "");
    setGradoAcademicoId(
      initialData.grado_academico_actual?.id ??
        initialData.grado_academico_id ??
        null
    );
    setRolActividadId(initialData.rol_actividad_id ?? null);
    setFechaInicio(
      initialData.fecha_inicio
        ? new Date(`${initialData.fecha_inicio}T00:00:00`)
        : null
    );
    setFechaFin(
      initialData.fecha_fin
        ? new Date(`${initialData.fecha_fin}T00:00:00`)
        : null
    );
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "produccion-docencia",
    recordId: id,
    value: { investigadorId, curso, institucion, fechaInicio: toCivilDateString(fechaInicio), fechaFin: toCivilDateString(fechaFin), gradoAcademicoId, rolActividadId },
    ready: !isEdit || (!isLoading && Boolean(initialData)),
    autosave: false,
    hasContent: (draft) => Boolean(draft.investigadorId || draft.curso || draft.institucion || draft.fechaInicio || draft.fechaFin || draft.gradoAcademicoId || draft.rolActividadId),
    onRestore: (draft) => { setInvestigadorId(draft.investigadorId); setCurso(draft.curso); setInstitucion(draft.institucion); setFechaInicio(draft.fechaInicio ? new Date(`${draft.fechaInicio}T00:00:00`) : null); setFechaFin(draft.fechaFin ? new Date(`${draft.fechaFin}T00:00:00`) : null); setGradoAcademicoId(draft.gradoAcademicoId); setRolActividadId(draft.rolActividadId); },
  });

  const formatDateStr = (date: Date | null) => {
    if (!date) return null;
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  };

  const getInitialInvestigadorId = () =>
    initialData?.investigador_id ??
    (typeof initialData?.investigador === "object"
      ? initialData?.investigador?.id ?? null
      : null);

  const getInitialGradoAcademicoId = () =>
    initialData?.grado_academico_actual?.id ??
    initialData?.grado_academico_id ??
    null;

  const mutation = useMutation({
    mutationFn: (payload: Partial<ActividadDocenciaPayload>) =>
      isEdit
        ? actualizarActividadDocencia(Number(id), payload)
        : crearActividadDocencia(payload as ActividadDocenciaPayload),
    onSuccess: async () => {
      clearDraft();
      await qc.invalidateQueries({ queryKey: ["docencia"] });
      await qc.invalidateQueries({ queryKey: ["actividad-docencia", id] });

      if (isEdit && id) {
        navigate(`/docenciaInvestigador/${id}`, {
          replace: true,
          state: {
            successMessage: "Actividad en docencia actualizada con éxito.",
          },
        });
        return;
      }

      navigate("/docenciaInvestigador", {
        state: {
          successMessage: "Actividad en docencia creada con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["investigador","curso","institucion","fechaInicio","fechaFin","gradoAcademico","rolActividad"])) return;
      setErrorMessage(
        getErrorMessage(
          error,
          isEdit
            ? "Lo sentimos, no pudimos actualizar la actividad de docencia. Revise los datos e intente nuevamente."
            : "Lo sentimos, no pudimos crear la actividad de docencia. Revise los datos e intente nuevamente."
        )
      );

      setShowError(true);
    },
  });

  const clearError = (field: string) => {
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!investigadorId) {
      newErrors.investigador = "Debe seleccionar investigador";
    }
    if (!curso.trim()) newErrors.curso = "Debe ingresar curso";
    if (!institucion.trim()) {
      newErrors.institucion = "Debe ingresar institución";
    }
    if (!fechaInicio) {
      newErrors.fechaInicio = "Debe seleccionar fecha de inicio";
    }
    if (!fechaFin) newErrors.fechaFin = "Debe seleccionar fecha de fin";
    if (!gradoAcademicoId) {
      newErrors.gradoAcademico = "Debe seleccionar grado academico";
    }
    if (!rolActividadId) {
      newErrors.rolActividad = "Debe seleccionar rol";
    }

    if (fechaInicio && fechaFin && fechaFin < fechaInicio) {
      newErrors.fechaFin =
        "La fecha de fin no puede ser anterior a la fecha de inicio";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mutation.isPending) return;
    if (!validate()) return;

    const payload = {
      investigador_id: investigadorId!,
      curso,
      institucion,
      fecha_inicio: formatDateStr(fechaInicio)!,
      fecha_fin: formatDateStr(fechaFin)!,
      grado_academico_id: gradoAcademicoId!,
      rol_actividad_id: rolActividadId!,
    };

    if (!isEdit) {
      mutation.mutate(payload);
      return;
    }

    const initialPayload = {
      investigador_id: getInitialInvestigadorId(),
      curso: initialData?.curso ?? "",
      institucion: initialData?.institucion ?? "",
      fecha_inicio: initialData?.fecha_inicio ?? null,
      fecha_fin: initialData?.fecha_fin ?? null,
      grado_academico_id: getInitialGradoAcademicoId(),
      rol_actividad_id: initialData?.rol_actividad_id ?? null,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    if (Object.keys(changedPayload).length === 0) {
      clearDraft();
      navigate(`/docenciaInvestigador/${id}`, {
        replace: true,
        state: {
          successMessage: "No hubo cambios para actualizar.",
        },
      });
      return;
    }

    mutation.mutate(changedPayload);
  };

  if (isEdit && isLoading) return <LoadingSkeleton variant="form" label="Cargando actividad..." />;

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl md:text-3xl font-semibold leading-none">
        {isEdit
          ? "Editar actividad en docencia"
          : "Nueva actividad en docencia"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Investigador" name="investigador" error={errors.investigador}>
          <>
            <select
              className={`${inputClass("investigador")} ${
                !investigadorId ? "text-slate-400" : "text-slate-900"
              }`}
              value={investigadorId ?? ""}
              onChange={(e) => {
                const value = e.target.value ? Number(e.target.value) : null;
                setInvestigadorId(value);
                if (value) clearError("investigador");
              }}
            >
              <option value="" disabled>
                Seleccionar investigador
              </option>
              {investigadores.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.nombre_apellido}
                </option>
              ))}
            </select>
            {errors.investigador && (
              <p className="mt-1 text-sm text-red-500">{errors.investigador}</p>
            )}
          </>
        </Field>

        <Field required label="Curso" name="curso" error={errors.curso}>
          <>
            <input
              className={inputClass("curso")}
              value={curso}
              placeholder="Ej: Diseño de Sistemas"
              onChange={(e) => {
                setCurso(e.target.value);
                if (e.target.value.trim()) clearError("curso");
              }}
            />
            {errors.curso && (
              <p className="mt-1 text-sm text-red-500">{errors.curso}</p>
            )}
          </>
        </Field>

        <Field required label="Institución" name="institucion" error={errors.institucion}>
          <>
            <input
              className={inputClass("institucion")}
              value={institucion}
              placeholder="Ej: UTN Facultad Regional La Plata"
              onChange={(e) => {
                setInstitucion(e.target.value);
                if (e.target.value.trim()) clearError("institucion");
              }}
            />
            {errors.institucion && (
              <p className="mt-1 text-sm text-red-500">{errors.institucion}</p>
            )}
          </>
        </Field>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Field required label="Fecha inicio" name="fechaInicio" error={errors.fechaInicio}>
            <>
              <Calendar
                value={fechaInicio}
                onChange={(date) => {
                  setFechaInicio(date);
                  if (date) clearError("fechaInicio");
                }}
                className={inputClass("fechaInicio")}
                helperText="DD/MM/AAAA"
              />
            </>
          </Field>

          <Field required label="Fecha fin" name="fechaFin" error={errors.fechaFin}>
            <>
              <Calendar
                value={fechaFin}
                onChange={(date) => {
                  setFechaFin(date);
                  if (date) clearError("fechaFin");
                }}
                minDate={fechaInicio ?? undefined}
                className={inputClass("fechaFin")}
                helperText="DD/MM/AAAA"
              />
            </>
          </Field>
        </div>

        <Field required label="Grado academico" name="gradoAcademico" error={errors.gradoAcademico}>
          <>
            <select
              className={`${inputClass("gradoAcademico")} ${
                !gradoAcademicoId ? "text-slate-400" : "text-slate-900"
              }`}
              value={gradoAcademicoId ?? ""}
              onChange={(e) => {
                const value = e.target.value ? Number(e.target.value) : null;
                setGradoAcademicoId(value);
                if (value) clearError("gradoAcademico");
              }}
            >
              <option value="" disabled>
                Seleccionar grado academico
              </option>
              {gradosAcademicos.map((grado) => (
                <option key={grado.id} value={grado.id}>
                  {grado.nombre}
                </option>
              ))}
            </select>
            {errors.gradoAcademico && (
              <p className="mt-1 text-sm text-red-500">
                {errors.gradoAcademico}
              </p>
            )}
          </>
        </Field>

        <Field required label="Rol en la actividad" name="rolActividad" error={errors.rolActividad}>
          <>
            <select
              className={`${inputClass("rolActividad")} ${
                !rolActividadId ? "text-slate-400" : "text-slate-900"
              }`}
              value={rolActividadId ?? ""}
              onChange={(e) => {
                const value = e.target.value ? Number(e.target.value) : null;
                setRolActividadId(value);
                if (value) clearError("rolActividad");
              }}
            >
              <option value="" disabled>
                Seleccionar rol en la actividad
              </option>
              {rolesActividad.map((rol) => (
                <option key={rol.id} value={rol.id}>
                  {rol.nombre}
                </option>
              ))}
            </select>
            {errors.rolActividad && (
              <p className="mt-1 text-sm text-red-500">{errors.rolActividad}</p>
            )}
          </>
        </Field>

        <div className="flex justify-between pt-6">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => requestLeave(() => navigate(-1))}
          >
            Volver
          </Button>

          <Button type="submit" size="sm" disabled={mutation.isPending} loading={mutation.isPending} loadingText="Guardando...">
            {mutation.isPending
              ? isEdit
                ? "Actualizando..."
                : "Guardando..."
              : isEdit
                ? "Actualizar"
                : "Guardar"}
          </Button>
        </div>
      </form>

      <SuccessToast
        open={showError}
        message={errorMessage}
        onClose={() => setShowError(false)}
        variant="error"
      />
    </section>
  );
}
