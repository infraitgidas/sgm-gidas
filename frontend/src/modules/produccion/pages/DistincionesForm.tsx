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
import {
  crearDistincion,
  getDistincionById,
  actualizarDistincion,
  type DistincionPayload,
} from "@/modules/produccion/services/distincionesServices";
import {
  getProyectos,
  type Proyecto,
} from "@/modules/proyectos/services/proyectosServices";
import { useUct } from "@/modules/grupo/hooks/useUct";
import { toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";

export default function DistincionesForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { uct } = useUct();
  const { user } = useAuth();

  const isEdit = Boolean(id);

  const proyectosQuery = useQuery({
    queryKey: ["proyectos", "activos"],
    queryFn: () => getProyectos(),
    staleTime: 60_000,
  });
  const proyectos = proyectosQuery.data ?? [];

  const { data: initialData, isLoading, isError } = useQuery({
    queryKey: ["distincion", id],
    queryFn: () => (id ? getDistincionById(Number(id)) : null),
    enabled: isEdit,
  });

  const [fecha, setFecha] = useState<Date | null>(null);
  const [descripcion, setDescripcion] = useState("");
  const [proyectoId, setProyectoId] = useState<number | null>(null);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!initialData) return;

    setFecha(initialData.fecha ? new Date(`${initialData.fecha}T00:00:00`) : null);
    setDescripcion(initialData.descripcion ?? "");
    setProyectoId(initialData.proyecto?.id ?? null);
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "produccion-distinciones",
    recordId: id,
    value: { fecha: toCivilDateString(fecha), descripcion, proyectoId },
    ready: !isEdit || (!isLoading && Boolean(initialData)),
    autosave: false,
    hasContent: (draft) => Boolean(draft.fecha || draft.descripcion || draft.proyectoId),
    onRestore: (draft) => { setFecha(draft.fecha ? new Date(`${draft.fecha}T00:00:00`) : null); setDescripcion(draft.descripcion); setProyectoId(draft.proyectoId); },
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

    if (!fecha) {
      newErrors.fecha = "Debe seleccionar fecha";
    }

    if (!descripcion.trim()) {
      newErrors.descripcion = "Debe ingresar descripción";
    }

    if (!proyectoId) {
      newErrors.proyecto = "Debe seleccionar un proyecto de investigación";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const mutation = useMutation({
    mutationFn: (payload: Partial<DistincionPayload>) =>
      isEdit
        ? actualizarDistincion(Number(id), payload)
        : crearDistincion(payload as DistincionPayload),
    onSuccess: async (saved) => {
      clearDraft();
      const distincionId = isEdit ? Number(id) : saved.id;

      await qc.invalidateQueries({ queryKey: ["distinciones"] });
      await qc.invalidateQueries({ queryKey: ["distincion", distincionId] });
      await qc.invalidateQueries({ queryKey: ["distincion-historial", distincionId] });

      navigate(isEdit ? `/distinciones/${distincionId}` : "/distinciones", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Distinción actualizada con éxito."
            : "Distinción creada con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["fecha","descripcion","proyecto"])) return;
      const backendMessage = getErrorMessage(
        error,
        isEdit
          ? "Lo sentimos, no pudimos actualizar la distinción. Revise los datos e intente nuevamente."
          : "Lo sentimos, no pudimos crear la distinción. Revise los datos e intente nuevamente."
      );
      setErrorMessage(backendMessage);
      setShowError(true);
    },
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mutation.isPending) return;
    if (!validate()) return;
    if (!uct) return;

    const payload = {
      fecha: toCivilDateString(fecha)!,
      descripcion: descripcion.trim(),
      proyecto_investigacion_id: proyectoId!,
    };

    if (!isEdit) {
      await mutation.mutateAsync(payload);
      return;
    }

    const initialPayload = {
      fecha: initialData?.fecha ?? null,
      descripcion: initialData?.descripcion ?? "",
      proyecto_investigacion_id: initialData?.proyecto?.id ?? null,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    if (Object.keys(changedPayload).length === 0) {
      clearDraft();
      navigate(`/distinciones/${id}`, {
        replace: true,
        state: {
          successMessage: "No hubo cambios para actualizar.",
        },
      });
      return;
    }

    await mutation.mutateAsync(changedPayload);
  };

  if (isEdit && isLoading) {
    return <LoadingSkeleton variant="form" label="Cargando distinción..." />;
  }

  if ((isEdit && isError) || proyectosQuery.isError) {
    return (
      <p role="alert" className="text-slate-500">
        Lo sentimos, no pudimos recuperar la información. Intente nuevamente.
      </p>
    );
  }

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar distinción" : "Nueva distinción recibida"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Fecha" name="fecha" error={errors.fecha}>
          <Calendar
            value={fecha}
            onChange={(date) => {
              setFecha(date);
              if (date) clearError("fecha");
            }}
            className={inputClass("fecha")}
            helperText="DD/MM/AAAA"
          />
        </Field>

        <Field required label="Descripción" name="descripcion" error={errors.descripcion}>
          <textarea
            className={`${inputClass("descripcion")} min-h-[80px]`}
            value={descripcion}
            onChange={(e) => {
              setDescripcion(e.target.value);
              if (e.target.value.trim()) clearError("descripcion");
            }}
            placeholder="Ej.: Reconocimiento por aporte científico"
          />
        </Field>

        <Field required label="Proyecto de investigación" name="proyecto" error={errors.proyecto}>
          <select
            className={`${inputClass("proyecto")} ${
              !proyectoId ? "text-slate-400" : "text-slate-900"
            }`}
            value={proyectoId ?? ""}
            onChange={(e) => {
              const value = e.target.value ? Number(e.target.value) : null;
              setProyectoId(value);
              if (value) clearError("proyecto");
            }}
          >
            <option value="" disabled>
              Seleccionar proyecto
            </option>
            {proyectos.map((p: Proyecto) => (
              <option key={p.id} value={p.id}>
                {p.codigoProyecto} - {p.nombreProyecto}
              </option>
            ))}
          </select>
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

          <Button type="submit" size="sm" disabled={mutation.isPending || !uct} loading={mutation.isPending} loadingText="Guardando...">
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
