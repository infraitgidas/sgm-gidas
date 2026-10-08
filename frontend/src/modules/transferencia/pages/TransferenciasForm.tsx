import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors } from "@/lib/httpError";
import { hasLetter } from "../../../lib/textValidation";
import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import Button from "@/components/Button";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import DatePicker from "@/components/Calendar";
import Field from "@/components/Field";
import AdoptantesField from "@/modules/transferencia/components/AdoptantesField";
import SuccessToast from "@/components/SuccessToast";
import { getErrorMessage } from "@/lib/httpError";
import {
  createTransferencia,
  getTransferenciaById,
  updateTransferencia,
  type Transferencia,
  type TransferenciaPayload,
} from "@/modules/transferencia/services/transferenciasServices";
import type { Adoptante } from "@/modules/transferencia/services/adoptantesServices";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { useTiposContrato } from "@/modules/transferencia/hooks/useTransferencias";
import { toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";

export default function TransferenciasForm() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { uct, uctGuard } = useUctGuard();
  const { user } = useAuth();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;

  const { tipos, isError: isTiposError, refetch: refetchTipos } = useTiposContrato();

  const [data, setData] = useState({
    denominacion: "",
    demandante: "",
    descripcionActividad: "",
    monto: "",
    fechaInicio: "",
    fechaFin: "",
    tipoContratoId: "",
  });
  const [adoptantes, setAdoptantes] = useState<Adoptante[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const loadedId = useRef<number | null>(null);

  const {
    data: transferencia,
    isLoading,
    isError: isTransferenciaError,
    refetch: refetchTransferencia,
  } = useQuery<Transferencia | null>({
    queryKey: ["transferencias", id],
    queryFn: () => getTransferenciaById(Number(id)),
    enabled: isEdit,
  });

  useEffect(() => {
    if (!transferencia || loadedId.current === transferencia.id) return;
    loadedId.current = transferencia.id;

    setData({
      denominacion: transferencia.denominacion ?? "",
      demandante: transferencia.demandante ?? "",
      descripcionActividad: transferencia.descripcionActividad ?? "",
      monto: transferencia.monto?.toString() ?? "",
      fechaInicio: transferencia.fechaInicio ?? "",
      fechaFin: transferencia.fechaFin ?? "",
      tipoContratoId: transferencia.tipoContratoId?.toString() ?? "",
    });
    setAdoptantes(transferencia.adoptantes ?? []);
  }, [transferencia]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "transferencia",
    recordId: id,
    value: { data, adoptantes },
    ready: !isEdit || (!isLoading && Boolean(transferencia)),
    autosave: false,
    hasContent: (draft) => Object.values(draft.data).some(Boolean) || draft.adoptantes.length > 0,
    onRestore: (draft) => { setData(draft.data); setAdoptantes(draft.adoptantes); },
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

    if (!data.denominacion.trim() || data.denominacion.trim().length < 3) {
      newErrors.denominacion = "Debe ingresar una denominación válida";
    } else if (!hasLetter(data.denominacion)) {
      newErrors.denominacion = "La denominación debe contener letras";
    }

    if (!data.demandante.trim() || data.demandante.trim().length < 3) {
      newErrors.demandante = "Debe ingresar un demandante válido";
    } else if (!hasLetter(data.demandante)) {
      newErrors.demandante = "El demandante debe contener letras";
    }

    if (!data.descripcionActividad.trim() || data.descripcionActividad.trim().length < 10) {
      newErrors.descripcionActividad =
        "La descripción debe tener al menos 10 caracteres";
    }

    const monto = Number(data.monto);
    if (!Number.isFinite(monto) || monto <= 0) {
      newErrors.monto = "El monto debe ser mayor a 0";
    }

    if (!data.fechaInicio) {
      newErrors.fechaInicio = "Debe ingresar fecha de inicio";
    }

    if (data.fechaInicio && data.fechaFin && data.fechaFin < data.fechaInicio) {
      newErrors.fechaFin = "La fecha de fin no puede ser anterior a la de inicio";
    }

    if (!data.tipoContratoId) {
      newErrors.tipoContratoId = "Debe seleccionar tipo de contrato";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const { mutateAsync, isPending } = useMutation({
    mutationFn: async () => {
      if (!uct) {
        throw new Error("Grupo no disponible");
      }

      const payload = {
        denominacion: data.denominacion.trim(),
        demandante: data.demandante.trim(),
        descripcionActividad: data.descripcionActividad.trim(),
        monto: Number(data.monto),
        fechaInicio: data.fechaInicio,
        fechaFin: data.fechaFin || undefined,
        tipoContratoId: Number(data.tipoContratoId),
        grupoUtnId: uct.id,
      };

      if (!isEdit) {
        const created = await createTransferencia({
          ...payload,
          adoptantesIds: adoptantes.filter((adoptante) => adoptante.id > 0).map((adoptante) => adoptante.id),
          adoptantesNuevos: adoptantes.filter((adoptante) => adoptante.id < 0).map((adoptante) => adoptante.nombre),
        });
        return created;
      }

      const initialPayload = {
        denominacion: transferencia?.denominacion ?? "",
        demandante: transferencia?.demandante ?? "",
        descripcionActividad: transferencia?.descripcionActividad ?? "",
        monto: transferencia?.monto ?? 0,
        fechaInicio: transferencia?.fechaInicio ?? "",
        fechaFin: transferencia?.fechaFin ?? undefined,
        tipoContratoId: transferencia?.tipoContratoId ?? 0,
        grupoUtnId: transferencia?.grupoUtnId ?? uct.id,
      };

      const changedPayload: Partial<TransferenciaPayload> = Object.fromEntries(
        Object.entries(payload).filter(([key, value]) => {
          return initialPayload[key as keyof typeof initialPayload] !== value;
        })
      );
      // El grupo de la transferencia se fija en el alta.
      delete changedPayload.grupoUtnId;

      const prevIds = transferencia?.adoptantes.map((adoptante) => adoptante.id) ?? [];
      const nextIds = adoptantes.filter((adoptante) => adoptante.id > 0).map((adoptante) => adoptante.id);
      const nuevos = adoptantes.filter((adoptante) => adoptante.id < 0).map((adoptante) => adoptante.nombre);
      if (nuevos.length > 0 || nextIds.length !== prevIds.length || nextIds.some((adoptanteId) => !prevIds.includes(adoptanteId))) {
        changedPayload.adoptantesIds = nextIds;
        changedPayload.adoptantesNuevos = nuevos;
      }

      if (Object.keys(changedPayload).length === 0) {
        clearDraft();
        navigate(`/transferencias/${id}`, {
          replace: true,
          state: {
            successMessage: "No hubo cambios para actualizar.",
          },
        });
        return null;
      }

      return updateTransferencia(Number(id), changedPayload);
    },
    onSuccess: async (saved) => {
      if (!saved) return;
      clearDraft();

      const transferenciaId = isEdit ? Number(id) : saved.id;

      await qc.invalidateQueries({ queryKey: ["transferencias"] });
      await qc.invalidateQueries({ queryKey: ["transferencias", transferenciaId] });
      await qc.invalidateQueries({
        queryKey: ["transferencia-historial", transferenciaId],
      });
      await qc.invalidateQueries({ queryKey: ["adoptantes"] });

      navigate(isEdit ? `/transferencias/${transferenciaId}` : "/transferencias", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Transferencia actualizada con éxito."
            : "Transferencia creada con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["denominacion","demandante","descripcionActividad","monto","fechaInicio","fechaFin","tipoContratoId","adoptantes"])) return;
      setErrorMessage(
        getErrorMessage(
          error,
          isEdit
            ? "Lo sentimos, no pudimos actualizar la transferencia. Revise los datos e intente nuevamente."
            : "Lo sentimos, no pudimos crear la transferencia. Revise los datos e intente nuevamente."
        )
      );
      setShowError(true);
    },
  });

  if (isEdit && isLoading) {
    return <LoadingSkeleton variant="form" label="Cargando transferencia..." />;
  }

  if (isTiposError || isTransferenciaError) {
    return (
      <div role="alert" className="space-y-3 text-slate-600"><p>Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p><Button type="button" onClick={() => { if (isTiposError) void refetchTipos(); if (isTransferenciaError) void refetchTransferencia(); }}>Reintentar</Button></div>
    );
  }

  if (isEdit && !transferencia) {
    return <div role="alert" className="space-y-3 text-slate-600"><p>No se encontró la transferencia. Vuelva al listado e intente nuevamente.</p><Button type="button" onClick={() => navigate("/transferencias")}>Volver</Button></div>;
  }

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar transferencia" : "Nueva transferencia"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={async (e) => {
          e.preventDefault();
    if (isPending) return;
          if (!uct) return;
          if (!validate()) return;
          await mutateAsync();
        }}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Denominación" name="denominacion" error={errors.denominacion}>
          <>
            <input
              className={inputClass("denominacion")}
              value={data.denominacion}
              placeholder="Ej: Convenio de asistencia técnica"
              onChange={(e) => {
                setData((prev) => ({ ...prev, denominacion: e.target.value }));
                if (e.target.value.trim()) clearError("denominacion");
              }}
            />
            {errors.denominacion && (
              <p className="mt-1 text-sm text-red-500">{errors.denominacion}</p>
            )}
          </>
        </Field>

        <Field required label="Demandante" name="demandante" error={errors.demandante}>
          <>
            <input
              className={inputClass("demandante")}
              value={data.demandante}
              placeholder="Ej: Municipalidad de Resistencia"
              onChange={(e) => {
                setData((prev) => ({ ...prev, demandante: e.target.value }));
                if (e.target.value.trim()) clearError("demandante");
              }}
            />
            {errors.demandante && (
              <p className="mt-1 text-sm text-red-500">{errors.demandante}</p>
            )}
          </>
        </Field>

        <Field required label="Descripción de la actividad" name="descripcionActividad" error={errors.descripcionActividad}>
          <>
            <textarea
              rows={5}
              className={inputClass("descripcionActividad")}
              value={data.descripcionActividad}
              placeholder="Describir brevemente la actividad desarrollada"
              onChange={(e) => {
                setData((prev) => ({
                  ...prev,
                  descripcionActividad: e.target.value,
                }));
                if (e.target.value.trim()) clearError("descripcionActividad");
              }}
            />
            {errors.descripcionActividad && (
              <p className="mt-1 text-sm text-red-500">{errors.descripcionActividad}</p>
            )}
          </>
        </Field>

        <Field required label="Monto" name="monto" error={errors.monto}>
          <>
            <input
              type="number"
              step="0.01"
              min={0}
              className={inputClass("monto")}
              value={data.monto}
              placeholder="Ej: 250000"
              onChange={(e) => {
                setData((prev) => ({ ...prev, monto: e.target.value }));
                if (e.target.value) clearError("monto");
              }}
            />
            {errors.monto && <p className="mt-1 text-sm text-red-500">{errors.monto}</p>}
          </>
        </Field>

        <Field required label="Fecha de inicio" name="fechaInicio" error={errors.fechaInicio}>
          <DatePicker
            value={data.fechaInicio ? new Date(`${data.fechaInicio}T00:00:00`) : null}
            onChange={(dt) => {
              setData((prev) => ({
                ...prev,
                fechaInicio: toCivilDateString(dt) ?? "",
              }));
              if (dt) clearError("fechaInicio");
            }}
            helperText="DD/MM/AAAA"
            className={inputClass("fechaInicio")}
          />
        </Field>

        <Field label="Fecha de fin" name="fechaFin" error={errors.fechaFin}>
          <DatePicker
            value={data.fechaFin ? new Date(`${data.fechaFin}T00:00:00`) : null}
            onChange={(dt) => {
              setData((prev) => ({
                ...prev,
                fechaFin: toCivilDateString(dt) ?? "",
              }));
              clearError("fechaFin");
            }}
            helperText="Opcional"
            className={inputClass("fechaFin")}
          />
        </Field>

        <Field required label="Tipo de contrato" name="tipoContratoId" error={errors.tipoContratoId}>
          <>
            <select
              className={`${inputClass("tipoContratoId")} ${
                !data.tipoContratoId ? "text-slate-400" : "text-slate-900"
              }`}
              value={data.tipoContratoId}
              onChange={(e) => {
                setData((prev) => ({ ...prev, tipoContratoId: e.target.value }));
                if (e.target.value) clearError("tipoContratoId");
              }}
            >
              <option value="" disabled>
                Seleccionar tipo de contrato
              </option>
              {tipos.map((tipo) => (
                <option key={tipo.id} value={tipo.id}>
                  {tipo.nombre}
                </option>
              ))}
            </select>
            {errors.tipoContratoId && (
              <p className="mt-1 text-sm text-red-500">{errors.tipoContratoId}</p>
            )}
          </>
        </Field>

        <div data-error-field="adoptantes">
          <AdoptantesField selected={adoptantes} disabled={isPending} onChange={(next) => {
            setAdoptantes(next);
            setErrors((previous) => ({ ...previous, adoptantes: "" }));
          }} />
          {errors.adoptantes && <p role="alert" className="mt-1 text-sm text-red-600">{errors.adoptantes}</p>}
        </div>

        <div className="flex justify-between pt-6">
          <Button type="button" variant="secondary" size="sm" onClick={() => requestLeave(() => navigate(-1))}>
            Volver
          </Button>

          <Button type="submit" size="sm" disabled={isPending || !uct} loading={isPending} loadingText="Guardando...">
            {isPending ? "Guardando..." : isEdit ? "Actualizar" : "Guardar"}
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
