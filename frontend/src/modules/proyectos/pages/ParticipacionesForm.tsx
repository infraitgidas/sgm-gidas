import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import Button from "@/components/Button";
import Calendar from "@/components/Calendar";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";
import { useAuth } from "@/context/AuthContext";
import { applyFieldErrors, getErrorMessage } from "@/lib/httpError";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import { useBecarios } from "@/modules/personal/hooks/useBecarios";
import { useInvestigadores } from "@/modules/personal/hooks/useInvestigadores";
import ParticipanteField from "@/modules/proyectos/components/ParticipanteField";
import {
  actualizarParticipacion,
  crearParticipacion,
  getParticipacionById,
  type ParticipacionPayload,
  type ParticipanteRef,
} from "@/modules/proyectos/services/participacionesServices";
import {
  participanteClave,
  type ParticipanteBuscable,
} from "@/modules/proyectos/utils/participanteSearch";
import { hasLetter } from "@/lib/textValidation";
import { toCivilDateString } from "@/utils/dateTime";

const FORMAS_PARTICIPACION = [
  { value: "jurado", label: "Jurado" },
  { value: "evaluador", label: "Evaluador" },
  { value: "panelista", label: "Panelista" },
  { value: "comite", label: "Miembro de comité científico" },
];

const parseParticipante = (value: string): ParticipanteRef | null => {
  const [rol, rawId] = value.split(":");
  const id = Number(rawId);
  if ((rol !== "investigador" && rol !== "becario") || !Number.isInteger(id) || id <= 0) {
    return null;
  }
  return { rol, id };
};

export default function ParticipacionesForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEdit = Boolean(id);
  const { user } = useAuth();
  const investigadoresQuery = useInvestigadores();
  const becariosQuery = useBecarios();
  const initialQuery = useQuery({
    queryKey: ["participacion", id],
    queryFn: () => getParticipacionById(Number(id)),
    enabled: isEdit,
  });

  const [participanteValue, setParticipanteValue] = useState("");
  const [nombreEvento, setNombreEvento] = useState("");
  const [formaParticipacion, setFormaParticipacion] = useState("");
  const [fecha, setFecha] = useState<Date | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const initialData = initialQuery.data;
    if (!initialData) return;
    setParticipanteValue(`${initialData.participante.rol}:${initialData.participante.id}`);
    setNombreEvento(initialData.nombre_evento ?? "");
    setFormaParticipacion(initialData.forma_participacion ?? "");
    setFecha(initialData.fecha ? new Date(`${initialData.fecha}T00:00:00`) : null);
  }, [initialQuery.data]);

  const participantOptions = useMemo<ParticipanteBuscable[]>(() => {
    const options = new Map<string, ParticipanteBuscable>();
    for (const investigador of investigadoresQuery.data ?? []) {
      const participante: ParticipanteBuscable = {
        rol: "investigador",
        id: investigador.id,
        nombre_apellido: investigador.nombre_apellido,
        tipo: "Investigador",
      };
      options.set(participanteClave(participante), participante);
    }
    for (const becario of becariosQuery.data ?? []) {
      if (becario.activo === false) continue;
      const participante: ParticipanteBuscable = {
        rol: "becario",
        id: becario.id,
        nombre_apellido: becario.nombre_apellido,
        tipo: "Becario",
      };
      options.set(participanteClave(participante), participante);
    }
    if (initialQuery.data?.participante) {
      options.set(participanteClave(initialQuery.data.participante), initialQuery.data.participante);
    }
    return [...options.values()].sort((a, b) =>
      a.nombre_apellido.localeCompare(b.nombre_apellido, "es", { sensitivity: "base" })
    );
  }, [becariosQuery.data, initialQuery.data, investigadoresQuery.data]);

  const participanteSeleccionado = useMemo(() => {
    const referencia = parseParticipante(participanteValue);
    if (!referencia) return null;
    return participantOptions.find(
      (participante) => participanteClave(participante) === participanteClave(referencia)
    ) ?? null;
  }, [participantOptions, participanteValue]);

  const participantesNoDisponibles =
    investigadoresQuery.data === undefined || becariosQuery.data === undefined;
  const participantesConError = investigadoresQuery.isError || becariosQuery.isError;
  const participantesCargando = investigadoresQuery.isFetching || becariosQuery.isFetching;

  const draft = useFormDraft({
    userId: user?.id,
    module: "proyectos-participaciones",
    recordId: id,
    value: {
      participanteValue,
      nombreEvento,
      formaParticipacion,
      fecha: toCivilDateString(fecha)!,
    },
    ready: !isEdit || (!initialQuery.isLoading && Boolean(initialQuery.data)),
    autosave: false,
    hasContent: (value) => Boolean(
      value.participanteValue || value.nombreEvento || value.formaParticipacion || value.fecha
    ),
    onRestore: (value) => {
      setParticipanteValue(value.participanteValue);
      setNombreEvento(value.nombreEvento);
      setFormaParticipacion(value.formaParticipacion);
      setFecha(value.fecha ? new Date(`${value.fecha}T00:00:00`) : null);
    },
  });

  const clearError = (field: string) =>
    setErrors((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });

  const validate = () => {
    const next: Record<string, string> = {};
    if (!parseParticipante(participanteValue)) next.participante = "Seleccione un investigador o becario";
    if (!nombreEvento.trim()) next.nombreEvento = "Ingrese el nombre del evento";
    else if (!hasLetter(nombreEvento)) next.nombreEvento = "El nombre del evento debe contener letras";
    if (!formaParticipacion) next.formaParticipacion = "Seleccione una forma de participación";
    if (!fecha) next.fecha = "Seleccione una fecha";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const mutation = useMutation({
    mutationFn: (input: { mode: "create"; payload: ParticipacionPayload } | { mode: "edit"; payload: Partial<ParticipacionPayload> }) =>
      input.mode === "edit"
        ? actualizarParticipacion(Number(id), input.payload)
        : crearParticipacion(input.payload),
    onSuccess: async (saved) => {
      draft.clearDraft();
      const participacionId = isEdit ? Number(id) : saved.id;
      await queryClient.invalidateQueries({ queryKey: ["participaciones"] });
      await queryClient.invalidateQueries({ queryKey: ["participacion", participacionId] });
      await queryClient.invalidateQueries({ queryKey: ["participacion-historial", participacionId] });
      navigate(isEdit ? `/participaciones/${participacionId}` : "/participaciones", {
        replace: true,
        state: { successMessage: isEdit ? "Participación actualizada con éxito." : "Participación creada con éxito." },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["participante", "nombreEvento", "formaParticipacion", "fecha"])) return;
      setErrorMessage(getErrorMessage(error, "Lo sentimos, no pudimos guardar los cambios. Verifique los datos e intente nuevamente."));
      setShowError(true);
    },
  });

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (mutation.isPending || !validate()) return;
    const participante = parseParticipante(participanteValue)!;
    const payload: ParticipacionPayload = {
      participante,
      nombre_evento: nombreEvento.trim(),
      forma_participacion: formaParticipacion,
      fecha: toCivilDateString(fecha)!,
    };
    if (!isEdit) {
      await mutation.mutateAsync({ mode: "create", payload });
      return;
    }
    const initial = initialQuery.data!;
    const changed: Partial<ParticipacionPayload> = {};
    if (initial.participante.rol !== participante.rol || initial.participante.id !== participante.id) changed.participante = participante;
    if (initial.nombre_evento !== payload.nombre_evento) changed.nombre_evento = payload.nombre_evento;
    if (initial.forma_participacion !== payload.forma_participacion) changed.forma_participacion = payload.forma_participacion;
    if (initial.fecha !== payload.fecha) changed.fecha = payload.fecha;
    if (!Object.keys(changed).length) {
      draft.clearDraft();
      navigate(`/participaciones/${id}`, { replace: true, state: { successMessage: "No hubo cambios para actualizar." } });
      return;
    }
    await mutation.mutateAsync({ mode: "edit", payload: changed });
  };

  if (isEdit && initialQuery.isLoading) return <LoadingSkeleton variant="form" label="Cargando participación…" />;
  if (isEdit && initialQuery.isError) {
    return (
      <div role="alert" className="space-y-3 text-slate-600">
        <p>Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>
        <Button size="sm" onClick={() => initialQuery.refetch()}>Reintentar</Button>
      </div>
    );
  }

  const inputClass = (field: string) => `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">{isEdit ? "Editar participación" : "Nueva participación relevante"}</h2>
      {draft.availableDraft && <DraftRecoveryNotice savedAt={draft.availableDraft.saved_at} sourceChanged={draft.sourceChanged} onRestore={draft.restoreDraft} onDiscard={draft.discardDraft} />}
      <DraftLeaveControls blocker={draft.blocker} saveStatus={draft.saveStatus} keepAndLeave={draft.keepAndLeave} discardAndLeave={draft.discardAndLeave} />

      <form noValidate onSubmit={submit} className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6">
        <Field required label="Participante" name="participante" error={errors.participante}>
          <>
            {participantesConError && (
              <div className="space-y-2">
                <p role="alert" className="text-sm text-red-600">
                  Lo sentimos, no pudimos recuperar los participantes. Intente nuevamente.
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  loading={participantesCargando}
                  loadingText="Cargando participantes..."
                  onClick={() => {
                    if (investigadoresQuery.isError) void investigadoresQuery.refetch();
                    if (becariosQuery.isError) void becariosQuery.refetch();
                  }}
                >
                  Reintentar
                </Button>
              </div>
            )}
            {!participantesConError && participantesNoDisponibles && (
              <LoadingSkeleton variant="compact" label="Cargando participantes..." />
            )}
            {!participantesConError && !participantesNoDisponibles && participantOptions.length === 0 && (
              <p role="status" className="text-sm text-slate-500">
                No hay investigadores o becarios activos disponibles.
              </p>
            )}
            <ParticipanteField
              value={participanteSeleccionado}
              options={participantOptions}
              disabled={participantesNoDisponibles}
              onChange={(participante) => {
                setParticipanteValue(participante ? participanteClave(participante) : "");
                if (participante) clearError("participante");
              }}
            />
          </>
        </Field>

        <Field required label="Nombre del evento" name="nombreEvento" error={errors.nombreEvento}>
          <input className={inputClass("nombreEvento")} value={nombreEvento} onChange={(event) => { setNombreEvento(event.target.value); if (event.target.value.trim()) clearError("nombreEvento"); }} placeholder="Ej: Congreso Argentino de Ingeniería" />
        </Field>

        <Field required label="Forma de participación" name="formaParticipacion" error={errors.formaParticipacion}>
          <select className={`${inputClass("formaParticipacion")} ${formaParticipacion ? "text-slate-900" : "text-slate-400"}`} value={formaParticipacion} onChange={(event) => { setFormaParticipacion(event.target.value); clearError("formaParticipacion"); }}>
            <option value="" disabled>Seleccionar forma de participación</option>
            {FORMAS_PARTICIPACION.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </Field>

        <Field required label="Fecha" name="fecha" error={errors.fecha}>
          <Calendar value={fecha} onChange={(value) => { setFecha(value); if (value) clearError("fecha"); }} className={inputClass("fecha")} helperText="DD/MM/AAAA" />
        </Field>

        <div className="flex justify-between pt-6">
          <Button type="button" variant="secondary" size="sm" onClick={() => draft.requestLeave(() => navigate(-1))}>Volver</Button>
          <Button type="submit" size="sm" disabled={mutation.isPending || participantesNoDisponibles} loading={mutation.isPending} loadingText="Guardando…">{isEdit ? "Actualizar" : "Guardar"}</Button>
        </div>
      </form>
      <SuccessToast open={showError} message={errorMessage} onClose={() => setShowError(false)} variant="error" />
    </section>
  );
}
