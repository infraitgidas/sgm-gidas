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
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import {
  createArticulo,
  getArticuloById,
  updateArticulo,
  type ArticuloPayload,
} from "@/modules/produccion/services/articulosDivulgacionServices";

export default function ArticulosDivulgacionForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { uct, uctGuard } = useUctGuard();
  const { user } = useAuth();

  const isEdit = Boolean(id);

  const initialQuery = useQuery({
    queryKey: ["articulo-divulgacion", id],
    queryFn: () => (id ? getArticuloById(Number(id)) : null),
    enabled: isEdit,
  });
  const { data: initialData, isLoading } = initialQuery;

  const [titulo, setTitulo] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [fechaPublicacion, setFechaPublicacion] = useState<Date | null>(null);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!initialData) return;

    setTitulo(initialData.titulo ?? "");
    setDescripcion(initialData.descripcion ?? "");
    setFechaPublicacion(
      initialData.fecha_publicacion
        ? new Date(`${initialData.fecha_publicacion}T00:00:00`)
        : null
    );
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "produccion-articulos",
    recordId: id,
    value: { titulo, descripcion, fechaPublicacion: toCivilDateString(fechaPublicacion) },
    ready: !isEdit || (!isLoading && Boolean(initialData)),
    autosave: false,
    hasContent: (draft) => Boolean(draft.titulo || draft.descripcion || draft.fechaPublicacion),
    onRestore: (draft) => { setTitulo(draft.titulo); setDescripcion(draft.descripcion); setFechaPublicacion(draft.fechaPublicacion ? new Date(`${draft.fechaPublicacion}T00:00:00`) : null); },
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

    if (!titulo.trim()) {
      newErrors.titulo = "Debe ingresar título";
    } else if (titulo.trim().length < 5) {
      newErrors.titulo = "El título debe tener al menos 5 caracteres";
    }

    if (!descripcion.trim()) {
      newErrors.descripcion = "Debe ingresar descripción";
    } else if (descripcion.trim().length < 10) {
      newErrors.descripcion =
        "La descripción debe tener al menos 10 caracteres";
    }

    if (!fechaPublicacion) {
      newErrors.fecha = "Debe seleccionar fecha";
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
    mutationFn: (payload: Partial<ArticuloPayload>) =>
      isEdit
        ? updateArticulo(Number(id), payload)
        : createArticulo(payload as ArticuloPayload),
    onSuccess: async (saved) => {
      clearDraft();
      const articuloId = isEdit ? Number(id) : saved.id;

      await qc.invalidateQueries({ queryKey: ["articulos-divulgacion"] });
      await qc.invalidateQueries({ queryKey: ["articulo-divulgacion", articuloId] });
      await qc.invalidateQueries({
        queryKey: ["articulo-divulgacion-historial", articuloId],
      });

      navigate(isEdit ? `/articulos-divulgacion/${articuloId}` : "/articulos-divulgacion", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Artículo actualizado con éxito."
            : "Artículo creado con éxito.",
        },
      });
    },
    onError: (error) => {
      if (
        applyFieldErrors(
          error,
          setErrors,
          ["titulo", "descripcion", "fecha"]
        )
      ) return;
      const backendMessage = getErrorMessage(
        error,
        isEdit
          ? "Lo sentimos, no pudimos actualizar el artículo. Revise los datos e intente nuevamente."
          : "Lo sentimos, no pudimos crear el artículo. Revise los datos e intente nuevamente."
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
      titulo: titulo.trim(),
      descripcion: descripcion.trim(),
      fecha_publicacion: formatDateStr(fechaPublicacion)!,
      grupo_utn_id: uct.id,
    };

    if (!isEdit) {
      await mutation.mutateAsync(payload);
      return;
    }

    const initialPayload = {
      titulo: initialData?.titulo ?? "",
      descripcion: initialData?.descripcion ?? "",
      fecha_publicacion: initialData?.fecha_publicacion ?? null,
      grupo_utn_id: uct.id,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    if (Object.keys(changedPayload).length === 0) {
      clearDraft();
      navigate(`/articulos-divulgacion/${id}`, {
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
    return <LoadingSkeleton variant="form" label="Cargando artículo..." />;
  }

  if (isEdit && (initialQuery.isError || !initialData)) {
    return (
      <div role="alert" className="space-y-3 text-slate-600">
        <p>Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>
        <Button type="button" variant="secondary" size="sm" onClick={() => initialQuery.refetch()}>
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
        {isEdit
          ? "Editar artículo de divulgación"
          : "Nuevo artículo de divulgación"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Título" name="titulo" error={errors.titulo}>
          <input
              type="text"
              className={inputClass("titulo")}
              value={titulo}
              onChange={(e) => {
                setTitulo(e.target.value);
                if (e.target.value.trim()) clearError("titulo");
              }}
              placeholder="Ej: Impacto de la investigación en la comunidad"
            />
        </Field>

        <Field required label="Descripción" name="descripcion" error={errors.descripcion}>
          <textarea
              className={`${inputClass("descripcion")} min-h-[100px]`}
              value={descripcion}
              onChange={(e) => {
                setDescripcion(e.target.value);
                if (e.target.value.trim()) clearError("descripcion");
              }}
              placeholder="Ej: Artículo orientado a la divulgación de resultados científicos para público general"
            />
        </Field>

        <Field required label="Fecha de publicación" name="fecha" error={errors.fecha}>
          <Calendar
            value={fechaPublicacion}
            onChange={(date) => {
              setFechaPublicacion(date);
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

      {uctGuard}
    </section>
  );
}
