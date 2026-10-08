import { getGruposUtn } from "@/modules/grupo/services/gruposUtnServices";
import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import Field from "@/components/Field";
import DatePicker from "@/components/Calendar";
import SuccessToast from "@/components/SuccessToast";
import { getErrorMessage } from "@/lib/httpError";
import { createMemoria } from "@/modules/memorias/services/memoriasService";
import { toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";

export default function MemoriaForm() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [grupoId, setGrupoId] = useState("");
  const { data: grupos = [], isLoading: cargandoGrupos, isError: errorGrupos } = useQuery({ queryKey: ["grupos-utn"], queryFn: getGruposUtn });
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFin, setPeriodoFin] = useState("");
  const [fechaApertura, setFechaApertura] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "memorias",
    value: { grupoId, periodoInicio, periodoFin, fechaApertura },
    autosave: false,
    hasContent: (draft) => Boolean(draft.grupoId || draft.periodoInicio || draft.periodoFin || draft.fechaApertura),
    onRestore: (draft) => { setGrupoId(draft.grupoId); setPeriodoInicio(draft.periodoInicio); setPeriodoFin(draft.periodoFin); setFechaApertura(draft.fechaApertura); },
  });

  const validate = () => {
    const nextErrors: Record<string, string> = {};

    if (!grupoId) nextErrors.grupo_utn_id = "Debe seleccionar una UCT.";

    if (!periodoInicio) {
      nextErrors.periodoInicio = "Debe ingresar el inicio del período.";
    }

    if (!periodoFin) {
      nextErrors.periodoFin = "Debe ingresar el fin del período.";
    }

    if (periodoInicio && periodoFin && periodoFin < periodoInicio) {
      nextErrors.periodoFin =
        "La fecha de fin no puede ser anterior al inicio del período.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) focusFieldErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const { mutateAsync, isPending } = useMutation({
    mutationFn: () =>
      createMemoria({
        grupo_utn_id: Number(grupoId),
        periodo_inicio: periodoInicio,
        periodo_fin: periodoFin,
        fecha_apertura: fechaApertura || undefined,
      }),
    onSuccess: async (memoria) => {
      clearDraft();
      await queryClient.invalidateQueries({ queryKey: ["memorias"] });
      await queryClient.invalidateQueries({ queryKey: ["memoria", memoria.id] });

      navigate("/memorias", {
        replace: true,
        state: { successMessage: "Memoria creada con éxito." },
      });
    },
    onError: (error) => {
      if (
        applyFieldErrors(error, setErrors, [
          "grupo_utn_id",
          "periodoInicio",
          "periodoFin",
          "fechaApertura",
        ])
      ) {
        return;
      }
      setErrorMessage(
        getErrorMessage(
          error,
          "Lo sentimos, no pudimos crear la memoria. Revise los datos e intente nuevamente."
        )
      );

      setShowError(true);
    },
  });

  const inputClass = (field: string) =>
    errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : "";

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        Nueva memoria
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
        onSubmit={async (event) => {
          event.preventDefault();
          if (isPending) return;
          if (!validate()) return;
          try { await mutateAsync(); } catch { /* onError muestra el mensaje */ }
        }}
      >
        <Field required label="UCT" name="grupo_utn_id" error={errors.grupo_utn_id}>
          <select id="grupo_utn_id" value={grupoId} disabled={cargandoGrupos || errorGrupos || isPending} onChange={(event) => {
            setGrupoId(event.target.value); setErrors((prev) => ({ ...prev, grupo_utn_id: "" }));
          }} className="w-full rounded-lg border border-slate-200 p-3">
            <option value="">Seleccione una UCT</option>
            {grupos.map((grupo) => <option key={grupo.id} value={grupo.id}>{grupo.nombre}</option>)}
          </select>
          {errorGrupos && <p role="alert">Lo sentimos, no pudimos recuperar las UCT. Intente nuevamente.</p>}
          {!cargandoGrupos && !errorGrupos && !grupos.length && <p role="status">Debe registrar una UCT antes de crear una memoria.</p>}
        </Field>
        <p className="text-sm text-slate-500">
          El período indica qué fechas abarca la memoria y puede cruzar años.
          La fecha de apertura indica cuándo comienza su carga.
        </p>
        <Button type="button" variant="secondary" size="sm" onClick={() => {
          const year = new Date().getFullYear();
          setPeriodoInicio(`${year}-01-01`);
          setPeriodoFin(`${year}-12-31`);
          setErrors({});
        }}>Usar año calendario actual</Button>
        <Field required label="Período de inicio" name="periodoInicio" error={errors.periodoInicio}>
          <DatePicker
            value={periodoInicio ? new Date(`${periodoInicio}T00:00:00`) : null}
            onChange={(date) => {
              setPeriodoInicio(toCivilDateString(date) ?? "");
              if (errors.periodoInicio) {
                setErrors((prev) => ({ ...prev, periodoInicio: "" }));
              }
            }}
            helperText="DD/MM/AAAA"
            className={inputClass("periodoInicio")}
          />
        </Field>

        <Field required label="Período de fin" name="periodoFin" error={errors.periodoFin}>
          <DatePicker
            value={periodoFin ? new Date(`${periodoFin}T00:00:00`) : null}
            onChange={(date) => {
              setPeriodoFin(toCivilDateString(date) ?? "");
              if (errors.periodoFin) {
                setErrors((prev) => ({ ...prev, periodoFin: "" }));
              }
            }}
            helperText="DD/MM/AAAA"
            className={inputClass("periodoFin")}
          />
        </Field>

        <Field label="Fecha de apertura" name="fechaApertura" error={errors.fechaApertura}>
          <DatePicker
            value={fechaApertura ? new Date(fechaApertura) : null}
            onChange={(date) => {
              setFechaApertura(date ? date.toISOString().slice(0, 19) : "");
              setErrors((prev) => ({ ...prev, fechaApertura: "" }));
            }}
            helperText="Opcional. Si no se informa, se usa la fecha actual."
            className={inputClass("fechaApertura")}
          />
        </Field>

        <div className="flex justify-between pt-6">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => requestLeave(() => navigate("/memorias"))}
          >
            Volver
          </Button>

          <Button type="submit" size="sm" disabled={isPending} loading={isPending} loadingText="Guardando...">
            {isPending ? "Guardando..." : "Guardar"}
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
