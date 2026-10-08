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
  createTrabajoRevista,
  updateTrabajoRevista,
  getTrabajoRevistaById,
  type TrabajoRevista,
  type TrabajoRevistaPayload,
} from "@/modules/produccion/services/trabajosRevistasServices";

import { useTiposRevista } from "@/modules/produccion/hooks/useTiposRevista";
import AutoresQueryFeedback from "@/modules/produccion/components/AutoresQueryFeedback";
import { useIntegrantesAutores } from "@/modules/produccion/hooks/useIntegrantesAutores";
import { mismasAutorias, type IntegranteAutor } from "@/modules/produccion/services/trabajoAutoresServices";
import { useAuth } from "@/context/AuthContext";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { toCivilDateString } from "@/utils/dateTime";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";

export default function TrabajosRevistasForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isEdit = Boolean(id);

  const { uct, uctGuard } = useUctGuard();
  const { tipos = [] } = useTiposRevista();
  const { canCreateRecords, canEditRecords, user } = useAuth();
  const puedeGuardar = isEdit ? canEditRecords() : canCreateRecords();
  const autoresQuery = useIntegrantesAutores();
  const integrantes = autoresQuery.data ?? [];
  const autoresNoDisponibles = autoresQuery.data === undefined;

  const { data: initialData, isLoading, refetch } = useQuery({
    queryKey: ["trabajo-revista", Number(id)],
    queryFn: () =>
      id ? getTrabajoRevistaById(Number(id)) : Promise.resolve(null),
    enabled: isEdit,
  });

  const [enlace, setEnlace] = useState("");
  const [titulo, setTitulo] = useState("");
  const [nombreRevista, setNombreRevista] = useState("");
  const [editorial, setEditorial] = useState("");
  const [issn, setIssn] = useState("");
  const [pais, setPais] = useState("");
  const [fecha, setFecha] = useState<Date | null>(null);
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
    setNombreRevista(initialData.nombre_revista ?? "");
    setEditorial(initialData.editorial ?? "");
    setIssn(initialData.issn ?? "");
    setPais(initialData.pais ?? "");
    setFecha(initialData.fecha_publicacion ? new Date(`${initialData.fecha_publicacion}T00:00:00`) : null);
    setTipoId(initialData.tipo_revista?.id ?? null);
    setAutores(initialData.autores ?? []);
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "produccion-revistas",
    recordId: id,
    value: { enlace, titulo, nombreRevista, editorial, issn, pais, fecha: toCivilDateString(fecha), tipoId, autores },
    ready: !isEdit || (!isLoading && Boolean(initialData)),
    autosave: false,
    hasContent: (draft) => Boolean(draft.enlace || draft.titulo || draft.nombreRevista || draft.editorial || draft.issn || draft.pais || draft.fecha || draft.tipoId || draft.autores.length),
    onRestore: (draft) => { setEnlace(draft.enlace); setTitulo(draft.titulo); setNombreRevista(draft.nombreRevista); setEditorial(draft.editorial); setIssn(draft.issn); setPais(draft.pais); setFecha(draft.fecha ? new Date(`${draft.fecha}T00:00:00`) : null); setTipoId(draft.tipoId); setAutores(draft.autores); },
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

    if (!titulo.trim()) newErrors.titulo = "Debe ingresar título";

    if (!nombreRevista.trim()) {
      newErrors.nombreRevista = "Debe ingresar nombre de revista";
    } else if (!hasLetter(nombreRevista)) {
      newErrors.nombreRevista = "El nombre de la revista debe contener letras";
    }

    if (!editorial.trim()) {
      newErrors.editorial = "Debe ingresar editorial";
    }

    if (!issn.trim()) {
      newErrors.issn = "Debe ingresar ISSN";
    }

    if (!pais.trim()) {
      newErrors.pais = "Debe ingresar país";
    }

    if (!tipoId) {
      newErrors.tipoId = "Debe seleccionar un tipo de revista";
    }

    if (!fecha) {
      newErrors.fecha = "Debe seleccionar la fecha de publicación";
    }

    if (autores.length === 0) {
      newErrors.autores = "Debe agregar al menos un autor";
    }

    const enlaceError = errorEnlace(enlace);
    if (enlaceError) newErrors.enlace = enlaceError;
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
    mutationFn: async (payload: Partial<TrabajoRevistaPayload>): Promise<TrabajoRevista> => {
      return isEdit ? updateTrabajoRevista(Number(id), payload) : createTrabajoRevista(payload as TrabajoRevistaPayload);
    },
    onSuccess: async (saved) => {
      clearDraft();
      const trabajoId = saved?.id ?? Number(id);

      await qc.invalidateQueries({ queryKey: ["trabajos-revistas"] });
      await qc.invalidateQueries({ queryKey: ["trabajo-revista", trabajoId] });
      await qc.invalidateQueries({ queryKey: ["trabajo-revista-historial", trabajoId] });

      navigate(isEdit ? `/trabajos-revistas/${trabajoId}` : "/trabajos-revistas", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Trabajo actualizado con éxito."
            : "Trabajo creado con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["enlace","titulo","nombreRevista","editorial","issn","pais","tipoId","fecha","autores"])) return;
      const backendMessage = getErrorMessage(
        error,
        isEdit
          ? "Lo sentimos, no pudimos actualizar el trabajo en revista. Revise los datos e intente nuevamente."
          : "Lo sentimos, no pudimos crear el trabajo en revista. Revise los datos e intente nuevamente."
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
      nombre_revista: toTitleCase(nombreRevista.trim()),
      editorial: toTitleCase(editorial.trim()),
      issn: issn.trim(),
      pais: toTitleCase(pais.trim()),
      fecha_publicacion: formatDateStr(fecha)!,
      tipo_revista_id: tipoId!,
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
      nombre_revista: initialData?.nombre_revista ?? "",
      editorial: initialData?.editorial ?? "",
      issn: initialData?.issn ?? "",
      pais: initialData?.pais ?? "",
      fecha_publicacion: initialData?.fecha_publicacion ?? null,
      tipo_revista_id: initialData?.tipo_revista?.id ?? null,
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
      navigate(`/trabajos-revistas/${id}`, {
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
    return <LoadingSkeleton variant="form" label="Cargando..." />;
  }

  if (isEdit && !initialData) {
    return <div role="alert" className="space-y-3"><p>Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>
      <Button type="button" onClick={() => { void refetch(); }}>Reintentar</Button></div>;
  }

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold md:text-3xl">
        {isEdit ? "Editar trabajo en revista" : "Nuevo trabajo en revista"}
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
              placeholder="Ej: Modelo de optimización aplicado a sistemas distribuidos"
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

        <Field required label="Nombre de la revista" name="nombreRevista" error={errors.nombreRevista}>
          <>
            <input
              className={inputClass("nombreRevista")}
              value={nombreRevista}
              placeholder="Ej: Journal of Computer Science"
              onChange={(e) => {
                setNombreRevista(e.target.value);
                if (e.target.value.trim()) clearError("nombreRevista");
              }}
              onBlur={() => {
                if (nombreRevista.trim()) {
                  setNombreRevista(toTitleCase(nombreRevista));
                }
              }}
            />
            {errors.nombreRevista && (
              <p className="mt-1 text-sm text-red-500">{errors.nombreRevista}</p>
            )}
          </>
        </Field>

        <Field required label="Editorial" name="editorial" error={errors.editorial}>
          <>
            <input
              className={inputClass("editorial")}
              value={editorial}
              placeholder="Ej: Elsevier"
              onChange={(e) => {
                setEditorial(e.target.value);
                if (e.target.value.trim()) clearError("editorial");
              }}
              onBlur={() => {
                if (editorial.trim()) setEditorial(toTitleCase(editorial));
              }}
            />
            {errors.editorial && (
              <p className="mt-1 text-sm text-red-500">{errors.editorial}</p>
            )}
          </>
        </Field>

        <Field required label="ISSN" name="issn" error={errors.issn}>
          <>
            <input
              className={inputClass("issn")}
              value={issn}
              placeholder="Ej: 1234-5678"
              onChange={(e) => {
                setIssn(e.target.value);
                if (e.target.value.trim()) clearError("issn");
              }}
            />
            {errors.issn && (
              <p className="mt-1 text-sm text-red-500">{errors.issn}</p>
            )}
          </>
        </Field>

        <Field required label="País" name="pais" error={errors.pais}>
          <>
            <input
              className={inputClass("pais")}
              value={pais}
              placeholder="Ej: Argentina"
              onChange={(e) => {
                setPais(e.target.value);
                if (e.target.value.trim()) clearError("pais");
              }}
              onBlur={() => {
                if (pais.trim()) setPais(toTitleCase(pais));
              }}
            />
            {errors.pais && (
              <p className="mt-1 text-sm text-red-500">{errors.pais}</p>
            )}
          </>
        </Field>

        <Field required label="Tipo de revista" name="tipoId" error={errors.tipoId}>
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
                Seleccionar tipo de revista
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

        <Field required label="Fecha de publicación" name="fecha" error={errors.fecha}>
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

        <div className="flex justify-between pt-6">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => requestLeave(() => navigate(-1))}
          >
            Volver
          </Button>

          <Button type="submit" size="sm" disabled={mutation.isPending || autoresNoDisponibles || !puedeGuardar || (isEdit && (!initialData || initialData.activo === false || !!initialData.deleted_at))} loading={mutation.isPending} loadingText="Guardando...">
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
