import LoadingSkeleton from "@/components/LoadingSkeleton";
import { errorEnlace, MAX_ENLACE } from "@/modules/produccion/utils/trabajoEnlace";
import { applyFieldErrors } from "@/lib/httpError";
import { hasLetter } from "../../../lib/textValidation";
import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Button from "@/components/Button";
import Calendar from "@/components/Calendar";
import IntegrantesAutoresField from "@/modules/produccion/components/IntegrantesAutoresField";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";

import { getErrorMessage } from "@/lib/httpError";
import { toTitleCase } from "@/utils/format";

import {
  createTrabajoReunion,
  updateTrabajoReunion,
  getTrabajoReunionById,
  type TrabajoReunion,
  type TrabajoReunionPayload,
} from "@/modules/produccion/services/trabajosReunionServices";

import { useTiposReunion } from "@/modules/produccion/hooks/useTiposReunion";
import AutoresQueryFeedback from "@/modules/produccion/components/AutoresQueryFeedback";
import { useIntegrantesAutores } from "@/modules/produccion/hooks/useIntegrantesAutores";
import { mismasAutorias, type IntegranteAutor } from "@/modules/produccion/services/trabajoAutoresServices";
import { useAuth } from "@/context/AuthContext";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { toCivilDateString } from "@/utils/dateTime";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";

export default function TrabajoReunionForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isEdit = Boolean(id);

  const { uct, uctGuard } = useUctGuard();
  const { tipos = [] } = useTiposReunion();
  const { canCreateRecords, canEditRecords, user } = useAuth();
  const puedeGuardar = isEdit ? canEditRecords() : canCreateRecords();
  const autoresQuery = useIntegrantesAutores();
  const integrantes = autoresQuery.data ?? [];
  const autoresNoDisponibles = autoresQuery.data === undefined;

  const { data: initialData, isLoading, refetch } = useQuery({
    queryKey: ["trabajo-reunion", Number(id)],
    queryFn: () => (id ? getTrabajoReunionById(Number(id)) : Promise.resolve(null)),
    enabled: isEdit,
  });

  const [enlace, setEnlace] = useState("");
  const [titulo, setTitulo] = useState("");
  const [nombreReunion, setNombreReunion] = useState("");
  const [procedencia, setProcedencia] = useState("");
  const [fechaPresentacion, setFechaPresentacion] = useState<Date | null>(null);
  const [tipoId, setTipoId] = useState<number | null>(null);
  const [autores, setAutores] = useState<IntegranteAutor[]>([]);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const datosCargadosId = useRef<number | null>(null);
  useEffect(() => {
    if (!initialData || datosCargadosId.current === initialData.id) return;
    datosCargadosId.current = initialData.id;

    setEnlace(initialData.enlace ?? "");
    setTitulo(initialData.titulo_trabajo ?? "");
    setNombreReunion(initialData.nombre_reunion ?? "");
    setProcedencia(initialData.procedencia ?? "");
    setFechaPresentacion(
      initialData.fecha_presentacion ? new Date(`${initialData.fecha_presentacion}T00:00:00`) : null
    );
    setTipoId(initialData.tipo_reunion?.id ?? null);
    setAutores(initialData.autores ?? []);
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "produccion-reuniones",
    recordId: id,
    value: { enlace, titulo, nombreReunion, procedencia, fechaPresentacion: toCivilDateString(fechaPresentacion), tipoId, autores },
    ready: !isEdit || (!isLoading && Boolean(initialData)),
    autosave: false,
    hasContent: (draft) => Boolean(draft.enlace || draft.titulo || draft.nombreReunion || draft.procedencia || draft.fechaPresentacion || draft.tipoId || draft.autores.length),
    onRestore: (draft) => { setEnlace(draft.enlace); setTitulo(draft.titulo); setNombreReunion(draft.nombreReunion); setProcedencia(draft.procedencia); setFechaPresentacion(draft.fechaPresentacion ? new Date(`${draft.fechaPresentacion}T00:00:00`) : null); setTipoId(draft.tipoId); setAutores(draft.autores); },
  });

  const formatDateStr = (date: Date | null) => {
    if (!date) return null;
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  };

  const clearError = (field: string) => {
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!titulo.trim()) {
      newErrors.titulo = "Debe ingresar título";
    }

    if (!nombreReunion.trim()) {
      newErrors.nombreReunion = "Debe ingresar nombre de reunión";
    } else if (!hasLetter(nombreReunion)) {
      newErrors.nombreReunion = "El nombre de la reunión debe contener letras";
    }

    if (!procedencia.trim()) {
      newErrors.procedencia = "Debe ingresar procedencia";
    }

    if (!tipoId) {
      newErrors.tipoId = "Debe seleccionar tipo de reunión";
    }

    if (!fechaPresentacion) {
      newErrors.fechaPresentacion = "Debe seleccionar la fecha de presentación";
    }

    if (autores.length === 0) {
      newErrors.autores = "Debe agregar al menos un autor";
    }

    const enlaceError = errorEnlace(enlace);
    if (enlaceError) newErrors.enlace = enlaceError;
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const mutation = useMutation({
    mutationFn: async (payload: Partial<TrabajoReunionPayload>): Promise<TrabajoReunion> => {
      return isEdit ? updateTrabajoReunion(Number(id), payload) : createTrabajoReunion(payload as TrabajoReunionPayload);
    },
    onSuccess: async (saved) => {
      clearDraft();
      const trabajoId = saved?.id ?? Number(id);

      await qc.invalidateQueries({ queryKey: ["trabajos-reunion"] });
      await qc.invalidateQueries({ queryKey: ["trabajo-reunion", trabajoId] });
      await qc.invalidateQueries({ queryKey: ["trabajo-reunion-historial", trabajoId] });

      navigate(isEdit ? `/trabajos-reunion/${trabajoId}` : "/trabajos-reunion", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Trabajo actualizado con éxito."
            : "Trabajo creado con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["enlace","titulo","nombreReunion","procedencia","tipoId","fechaPresentacion","autores"])) return;
      const backendMessage = getErrorMessage(
        error,
        isEdit
          ? "Lo sentimos, no pudimos actualizar el trabajo en reunión. Revise los datos e intente nuevamente."
          : "Lo sentimos, no pudimos crear el trabajo en reunión. Revise los datos e intente nuevamente.",
      );
      setErrorMessage(backendMessage);
      setShowError(true);
    },
  });

  const guardadoBloqueado = mutation.isPending || autoresNoDisponibles || !puedeGuardar || (isEdit && (!initialData || initialData.activo === false || !!initialData.deleted_at)) || !uct;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (guardadoBloqueado) return;
    if (!uct) return;
    if (!validate()) return;

    const payload = {
      enlace: enlace.trim() || null,
      autores: autores.map(({ id, rol }) => ({ id, rol })),
      titulo_trabajo: toTitleCase(titulo.trim()),
      nombre_reunion: toTitleCase(nombreReunion.trim()),
      procedencia: toTitleCase(procedencia.trim()),
      fecha_presentacion: formatDateStr(fechaPresentacion)!,
      tipo_reunion_id: tipoId!,
      grupo_utn_id: uct.id,
    };

    if (!isEdit) {
      await mutation.mutateAsync(payload).catch(() => undefined);
      return;
    }

    const initialPayload = {
      enlace: initialData?.enlace ?? null,
      autores: initialData?.autores ?? [],
      titulo_trabajo: initialData?.titulo_trabajo ?? "",
      nombre_reunion: initialData?.nombre_reunion ?? "",
      procedencia: initialData?.procedencia ?? "",
      fecha_presentacion: initialData?.fecha_presentacion ?? null,
      tipo_reunion_id: initialData?.tipo_reunion?.id ?? null,
      grupo_utn_id: uct.id,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        if (key === "autores") return !mismasAutorias(payload.autores, initialPayload.autores);
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    if (Object.keys(changedPayload).length === 0) {
      clearDraft();
      navigate(`/trabajos-reunion/${id}`, {
        replace: true,
        state: {
          successMessage: "No hubo cambios para actualizar.",
        },
      });
      return;
    }

    await mutation.mutateAsync(changedPayload).catch(() => undefined);
  };

  if (isEdit && isLoading) {
    return <LoadingSkeleton variant="form" label="Cargando trabajo..." />;
  }

  if (isEdit && !initialData) {
    return <div role="alert" className="space-y-3"><p>Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>
      <Button type="button" onClick={() => { void refetch(); }}>Reintentar</Button></div>;
  }

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar trabajo" : "Nuevo trabajo"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Título del trabajo" name="titulo" error={errors.titulo}>
          <>
            <input
              className={inputClass("titulo")}
              value={titulo}
              placeholder="Ej: Aplicación de modelos predictivos en sistemas complejos"
              onChange={(e) => {
                setTitulo(e.target.value);
                if (e.target.value.trim()) clearError("titulo");
              }}
              onBlur={() => {
                if (titulo.trim()) setTitulo(toTitleCase(titulo));
              }}
            />
            {errors.titulo && (
              <p className="mt-1 text-sm text-red-500">{errors.titulo}</p>
            )}
          </>
        </Field>

        <Field required label="Nombre de la reunión" name="nombreReunion" error={errors.nombreReunion}>
          <>
            <input
              className={inputClass("nombreReunion")}
              value={nombreReunion}
              placeholder="Ej: Congreso Argentino de Ingenieria"
              onChange={(e) => {
                setNombreReunion(e.target.value);
                if (e.target.value.trim()) clearError("nombreReunion");
              }}
              onBlur={() => {
                if (nombreReunion.trim()) {
                  setNombreReunion(toTitleCase(nombreReunion));
                }
              }}
            />
            {errors.nombreReunion && (
              <p className="mt-1 text-sm text-red-500">{errors.nombreReunion}</p>
            )}
          </>
        </Field>

        <Field required label="Procedencia" name="procedencia" error={errors.procedencia}>
          <>
            <input
              className={inputClass("procedencia")}
              value={procedencia}
              placeholder="Ej: Argentina"
              onChange={(e) => {
                setProcedencia(e.target.value);
                if (e.target.value.trim()) clearError("procedencia");
              }}
              onBlur={() => {
                if (procedencia.trim()) {
                  setProcedencia(toTitleCase(procedencia));
                }
              }}
            />
            {errors.procedencia && (
              <p className="mt-1 text-sm text-red-500">{errors.procedencia}</p>
            )}
          </>
        </Field>

        <Field required label="Tipo de reunión" name="tipoId" error={errors.tipoId}>
          <>
            <select
              className={`${inputClass("tipoId")} ${
                !tipoId ? "text-slate-400" : "text-slate-900"
              }`}
              value={tipoId ?? ""}
              onChange={(e) => {
                const value = e.target.value ? Number(e.target.value) : null;
                setTipoId(value);
                if (value) clearError("tipoId");
              }}
            >
              <option value="" disabled>
                Seleccionar tipo
              </option>
              {tipos.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
            {errors.tipoId && (
              <p className="mt-1 text-sm text-red-500">{errors.tipoId}</p>
            )}
          </>
        </Field>

        <Field label="Enlace al trabajo o DOI (opcional)" name="enlace" error={errors.enlace}>
          <input type="url" className={inputClass("enlace")} value={enlace}
            maxLength={MAX_ENLACE} placeholder="https://doi.org/10.1234/ejemplo"
            onChange={e => { setEnlace(e.target.value); clearError("enlace"); }} />
        </Field>

        <Field required label="Autores" name="autores" error={errors.autores}>
          <>
            <AutoresQueryFeedback query={autoresQuery} />
            <IntegrantesAutoresField value={autores} options={integrantes}
              disabled={guardadoBloqueado}
              onChange={value => { setAutores(value); if (value.length) clearError("autores"); }} />
          </>
        </Field>

        <Field required label="Fecha de presentación" name="fechaPresentacion" error={errors.fechaPresentacion}>
          <Calendar
            value={fechaPresentacion}
            onChange={(date) => {
              setFechaPresentacion(date);
              if (date) clearError("fechaPresentacion");
            }}
            className={inputClass("fechaPresentacion")}
            helperText="Desde 01/01/2010. Puede indicar una presentación programada."
          />
        </Field>

        <div className="flex justify-between pt-6">
          <Button type="button" variant="secondary" size="sm" onClick={() => requestLeave(() => navigate(-1))}>
            Volver
          </Button>

          <Button type="submit" size="sm" disabled={guardadoBloqueado} loading={mutation.isPending} loadingText="Guardando...">
            {mutation.isPending ? (isEdit ? "Actualizando..." : "Guardando...") : isEdit ? "Actualizar" : "Guardar"}
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
