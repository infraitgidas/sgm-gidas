import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors } from "@/lib/httpError";
import { hasLetter } from "../../../lib/textValidation";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import DatePicker from "@/components/Calendar";
import Field from "@/components/Field";
import React, { useState, useEffect } from "react";
import SuccessToast from "@/components/SuccessToast";
import { getErrorMessage } from "@/lib/httpError";
import {
  createEquipamiento,
  getEquipamientoById,
  updateEquipamiento,
  type EquipamientoPayload,
} from "@/modules/recursos/services/equipamientoServices";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import {
  EQUIPAMIENTO_MIN_FECHA_INCORPORACION,
  getLocalIsoDate,
  validateFechaIncorporacion,
} from "@/modules/recursos/utils/equipamientoValidation";
import { parseCivilDate, toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";

export default function EquipamientoForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { uct, uctGuard } = useUctGuard();
  const { user } = useAuth();

  const isEdit = Boolean(id);

  const { data: initial, isLoading } = useQuery({
    queryKey: ["equipamiento", id],
    queryFn: () => (id ? getEquipamientoById(Number(id)) : null),
    enabled: isEdit,
  });

  const [data, setData] = useState({
    denominacion: "",
    descripcion_breve: "",
    monto_invertido: undefined as number | undefined,
    fecha_incorporacion: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!initial) return;

    setData({
      denominacion: initial.denominacion ?? "",
      descripcion_breve: initial.descripcion_breve ?? "",
      monto_invertido: initial.monto_invertido ?? undefined,
      fecha_incorporacion: initial.fecha_incorporacion ?? "",
    });
  }, [initial]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "recursos-equipamiento",
    recordId: id,
    value: data,
    ready: !isEdit || (!isLoading && Boolean(initial)),
    autosave: false,
    hasContent: (draft) => Boolean(draft.denominacion || draft.descripcion_breve || draft.fecha_incorporacion || draft.monto_invertido),
    onRestore: setData,
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

    if (!data.denominacion.trim()) {
      newErrors.denominacion = "La denominación es obligatoria";
    } else if (!hasLetter(data.denominacion)) {
      newErrors.denominacion = "La denominación debe contener letras";
    }

    if (!data.descripcion_breve.trim()) {
      newErrors.descripcion = "La descripción es obligatoria";
    }

    const fechaError = validateFechaIncorporacion(data.fecha_incorporacion);
    if (fechaError) newErrors.fecha_incorporacion = fechaError;

    if (
      data.monto_invertido === undefined ||
      !Number.isFinite(data.monto_invertido) ||
      data.monto_invertido <= 0
    ) {
      newErrors.monto = "El monto debe ser mayor a 0";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const { mutateAsync, isPending } = useMutation({
    mutationFn: (payload: Partial<EquipamientoPayload>) =>
      isEdit
        ? updateEquipamiento(Number(id), payload)
        : createEquipamiento(payload as EquipamientoPayload),
    onSuccess: async (saved) => {
      clearDraft();
      const equipamientoId = isEdit ? Number(id) : saved.id;

      await qc.invalidateQueries({ queryKey: ["equipamiento"] });
      await qc.invalidateQueries({ queryKey: ["equipamiento", equipamientoId] });
      await qc.invalidateQueries({
        queryKey: ["equipamiento-historial", equipamientoId],
      });

      navigate(isEdit ? `/equipamiento/${equipamientoId}` : "/equipamiento", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Equipamiento actualizado con éxito."
            : "Equipamiento creado con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["denominacion","descripcion","fecha_incorporacion","monto"])) return;
      const backendMessage = getErrorMessage(
        error,
        isEdit
          ? "Lo sentimos, no pudimos actualizar el equipamiento. Revise los datos e intente nuevamente."
          : "Lo sentimos, no pudimos crear el equipamiento. Revise los datos e intente nuevamente."
      );
      setErrorMessage(backendMessage);
      setShowError(true);
    },
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isPending) return;
    if (!uct) return;
    if (!validate()) return;

    const payload = {
      grupo_utn_id: uct.id,
      denominacion: data.denominacion.trim(),
      descripcion_breve: data.descripcion_breve.trim(),
      fecha_incorporacion: data.fecha_incorporacion,
      monto_invertido: data.monto_invertido!,
    };

    if (!isEdit) {
      await mutateAsync(payload);
      return;
    }

    const initialPayload = {
      grupo_utn_id: uct.id,
      denominacion: initial?.denominacion ?? "",
      descripcion_breve: initial?.descripcion_breve ?? "",
      fecha_incorporacion: initial?.fecha_incorporacion ?? "",
      monto_invertido: initial?.monto_invertido ?? undefined,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    if (Object.keys(changedPayload).length === 0) {
      clearDraft();
      navigate(`/equipamiento/${id}`, {
        replace: true,
        state: {
          successMessage: "No hubo cambios para actualizar.",
        },
      });
      return;
    }

    await mutateAsync(changedPayload);
  };

  if (isLoading) return <LoadingSkeleton variant="form" label="Cargando..." />;

  const maxFechaIncorporacion = getLocalIsoDate();

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar equipamiento" : "Nuevo equipamiento"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Denominación" name="denominacion" error={errors.denominacion}>
          <>
            <input
              className={inputClass("denominacion")}
              value={data.denominacion}
              placeholder="Ej: Osciloscopio digital Tektronix"
              onChange={(e) => {
                setData((d) => ({
                  ...d,
                  denominacion: e.target.value,
                }));
                if (e.target.value.trim()) clearError("denominacion");
              }}
            />
            {errors.denominacion && (
              <p className="mt-1 text-sm text-red-500">{errors.denominacion}</p>
            )}
          </>
        </Field>

        <Field required label="Descripción breve" name="descripcion" error={errors.descripcion}>
          <>
            <input
              className={inputClass("descripcion")}
              value={data.descripcion_breve}
              placeholder="Describir brevemente el equipamiento y su uso"
              onChange={(e) => {
                setData((d) => ({
                  ...d,
                  descripcion_breve: e.target.value,
                }));
                if (e.target.value.trim()) clearError("descripcion");
              }}
            />
            {errors.descripcion && (
              <p className="mt-1 text-sm text-red-500">{errors.descripcion}</p>
            )}
          </>
        </Field>

        <Field required label="Monto invertido" name="monto" error={errors.monto}>
          <>
            <input
              type="number"
              step="0.01"
              min={0}
              className={inputClass("monto")}
              value={data.monto_invertido ?? ""}
              placeholder="Ej: 1250000"
              onChange={(e) => {
                const value = e.target.value ? Number(e.target.value) : undefined;

                setData((d) => ({
                  ...d,
                  monto_invertido: value,
                }));

                if (value && value > 0) clearError("monto");
              }}
            />
            {errors.monto && (
              <p className="mt-1 text-sm text-red-500">{errors.monto}</p>
            )}
          </>
        </Field>

        <Field required label="Fecha de incorporación" name="fecha_incorporacion" error={errors.fecha_incorporacion}>
          <DatePicker
            value={
              data.fecha_incorporacion
                ? new Date(`${data.fecha_incorporacion}T00:00:00`)
                : null
            }
            minDate={parseCivilDate(EQUIPAMIENTO_MIN_FECHA_INCORPORACION) ?? undefined}
            maxDate={parseCivilDate(maxFechaIncorporacion) ?? undefined}
            onChange={(dt) => {
              setData((d) => ({
                ...d,
                fecha_incorporacion: toCivilDateString(dt) ?? "",
              }));

              if (dt) clearError("fecha_incorporacion");
            }}
            helperText="Ingrese una fecha entre el 01/01/2010 y la fecha actual"
            className={inputClass("fecha_incorporacion")}
          />
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

          <Button type="submit" size="sm" disabled={isPending || !uct} loading={isPending} loadingText="Guardando...">
            {isPending
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
