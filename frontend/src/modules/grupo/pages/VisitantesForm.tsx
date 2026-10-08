import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors } from "@/lib/httpError";
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import Calendar from "@/components/Calendar";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";
import { getErrorMessage } from "@/lib/httpError";
import {
  actualizarVisitante,
  crearVisitante,
  getVisitanteById,
  type VisitantePayload,
} from "@/modules/grupo/services/visitantesServices";
import {
  getTiposVisita,
  type TipoVisita,
} from "@/modules/grupo/services/tiposVisitaServices";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";

export default function VisitantesForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const isEdit = Boolean(id);
  const { uct, uctGuard } = useUctGuard();
  const { user } = useAuth();

  const {
    data: tiposVisita = [],
    isLoading: isLoadingTiposVisita,
    isError: isErrorTiposVisita,
    refetch: refetchTiposVisita,
  } = useQuery({
    queryKey: ["tipos-visita"],
    queryFn: getTiposVisita,
    staleTime: 60_000,
  });

  const {
    data: initialData,
    isLoading,
    isError: isInitialDataError,
    refetch: refetchInitialData,
  } = useQuery({
    queryKey: ["visitante", id],
    queryFn: () => (id ? getVisitanteById(Number(id)) : null),
    enabled: isEdit,
  });

  const [razon, setRazon] = useState("");
  const [fecha, setFecha] = useState<Date | null>(null);
  const [procedencia, setProcedencia] = useState("");
  const [tipoVisitaId, setTipoVisitaId] = useState<number | null>(null);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!initialData) return;

    setRazon(initialData.razon ?? "");
    setFecha(initialData.fecha ? new Date(`${initialData.fecha}T00:00:00`) : null);
    setProcedencia(initialData.procedencia ?? "");
    setTipoVisitaId(initialData.tipo_visita_id ?? null);
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "grupo-visitantes",
    recordId: id,
    value: { razon, fecha: toCivilDateString(fecha), procedencia, tipoVisitaId },
    ready: !isEdit || (!isLoading && Boolean(initialData)),
    autosave: false,
    hasContent: (draft) => Boolean(draft.razon || draft.fecha || draft.procedencia || draft.tipoVisitaId),
    onRestore: (draft) => { setRazon(draft.razon); setFecha(draft.fecha ? new Date(`${draft.fecha}T00:00:00`) : null); setProcedencia(draft.procedencia); setTipoVisitaId(draft.tipoVisitaId); },
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

    if (!razon.trim()) {
      newErrors.razon = "Debe ingresar razon de la visita";
    }

    if (!fecha) {
      newErrors.fecha = "Debe seleccionar fecha";
    }

    if (!procedencia.trim()) {
      newErrors.procedencia = "Debe ingresar procedencia";
    } else if (!/[A-Za-zÁÉÍÓÚáéíóúÑñ]/.test(procedencia)) {
      newErrors.procedencia = "La procedencia no puede ser numerica.";
    }

    if (!tipoVisitaId) {
      newErrors.tipoVisita = "Debe seleccionar tipo de visita";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const formatDateStr = (date: Date | null) => {
    if (!date) return null;
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  };

  const mutation = useMutation({
    mutationFn: (
      input:
        | { mode: "create"; payload: VisitantePayload }
        | { mode: "edit"; payload: Partial<VisitantePayload> }
    ) =>
      input.mode === "edit"
        ? actualizarVisitante(Number(id), input.payload)
        : crearVisitante(input.payload),
    onSuccess: async (saved) => {
      clearDraft();
      const visitanteId = isEdit ? Number(id) : saved.id;

      await qc.invalidateQueries({ queryKey: ["visitantes"] });
      await qc.invalidateQueries({ queryKey: ["visitante", visitanteId] });
      await qc.invalidateQueries({
        queryKey: ["visitante-historial", visitanteId],
      });

      navigate(isEdit ? `/visitantes/${visitanteId}` : "/visitantes", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Visitante actualizado con éxito."
            : "Visitante creado con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["razon","fecha","procedencia","tipoVisita"])) return;
      setErrorMessage(getErrorMessage(error, isEdit
        ? "Lo sentimos, no pudimos actualizar la visita. Revise los datos e intente nuevamente."
        : "Lo sentimos, no pudimos crear la visita. Revise los datos e intente nuevamente."));
      setShowError(true);
    },
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mutation.isPending) return;
    if (!uct) return;
    if (!validate()) return;

    const payload = {
      razon: razon.trim(),
      fecha: formatDateStr(fecha)!,
      procedencia: procedencia.trim(),
      tipo_visita_id: tipoVisitaId!,
      grupo_utn_id: uct.id,
    };

    if (!isEdit) {
      await mutation.mutateAsync({ mode: "create", payload });
      return;
    }

    const initialPayload = {
      razon: initialData?.razon ?? "",
      fecha: initialData?.fecha ?? null,
      procedencia: initialData?.procedencia ?? "",
      tipo_visita_id: initialData?.tipo_visita_id ?? null,
      grupo_utn_id: uct.id,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    if (Object.keys(changedPayload).length === 0) {
      clearDraft();
      navigate(`/visitantes/${id}`, {
        replace: true,
        state: {
          successMessage: "No hubo cambios para actualizar.",
        },
      });
      return;
    }

    await mutation.mutateAsync({ mode: "edit", payload: changedPayload });
  };

  if ((isEdit && isLoading) || isLoadingTiposVisita) {
    return <LoadingSkeleton variant="form" label="Cargando visita..." />;
  }

  if (isEdit && isInitialDataError) {
    return (
      <div role="alert" className="space-y-4 text-slate-600">
        <p>Lo sentimos, no pudimos recuperar la visita. Intente nuevamente.</p>
        <Button type="button" variant="secondary" size="sm" onClick={() => void refetchInitialData()}>
          Reintentar
        </Button>
      </div>
    );
  }

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar visita" : "Nueva visita"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        {isErrorTiposVisita && (
          <div
            role="alert"
            className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 sm:flex-row sm:items-center sm:justify-between"
          >
            <p>
              Lo sentimos, no pudimos recuperar los tipos de visita. Intente nuevamente.
            </p>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void refetchTiposVisita()}
            >
              Reintentar
            </Button>
          </div>
        )}

        <Field required label="Razon de la visita" name="razon" error={errors.razon}>
          <>
            <textarea
              className={`${inputClass("razon")} min-h-[80px]`}
              value={razon}
              onChange={(e) => {
                setRazon(e.target.value);
                if (e.target.value.trim()) clearError("razon");
              }}
            />
            {errors.razon && (
              <p className="mt-1 text-sm text-red-500">{errors.razon}</p>
            )}
          </>
        </Field>

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

        <Field required label="Procedencia u origen" name="procedencia" error={errors.procedencia}>
          <>
            <input
              type="text"
              className={inputClass("procedencia")}
              value={procedencia}
              onChange={(e) => {
                setProcedencia(e.target.value);
                if (e.target.value.trim()) clearError("procedencia");
              }}
              placeholder="Ej.: Universidad Nacional de Córdoba"
            />
            {!errors.procedencia && (
              <p className="mt-1.5 text-xs text-slate-500">
                Indique la institución, ciudad o país desde donde proviene la visita.
              </p>
            )}
            {errors.procedencia && (
              <p className="mt-1 text-sm text-red-500">{errors.procedencia}</p>
            )}
          </>
        </Field>

        <Field required label="Tipo de visita" name="tipoVisita" error={errors.tipoVisita}>
          <>
            <select
              className={`${inputClass("tipoVisita")} ${
                !tipoVisitaId ? "text-slate-400" : "text-slate-900"
              }`}
              value={tipoVisitaId ?? ""}
              onChange={(e) => {
                const value = e.target.value ? Number(e.target.value) : null;
                setTipoVisitaId(value);
                if (value) clearError("tipoVisita");
              }}
            >
              <option value="" disabled>
                Seleccionar tipo de visita
              </option>
              {tiposVisita.map((t: TipoVisita) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
            {!errors.tipoVisita && (
              <p className="mt-1.5 text-xs text-slate-500">
                Clasifique el propósito de la visita, por ejemplo académica o intercambio.
              </p>
            )}
            {errors.tipoVisita && (
              <p className="mt-1 text-sm text-red-500">{errors.tipoVisita}</p>
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

          <Button type="submit" size="sm" disabled={mutation.isPending || !uct || isErrorTiposVisita || tiposVisita.length === 0} loading={mutation.isPending} loadingText="Guardando...">
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

      {uctGuard}
    </section>
  );
}
