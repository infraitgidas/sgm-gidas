import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors } from "@/lib/httpError";
import { hasOnlyLettersAndSpaces } from "../../../lib/textValidation";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import DocumentacionAutoresField from "@/modules/produccion/components/DocumentacionAutoresField";
import DatePicker from "@/components/Calendar";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";
import { getErrorMessage } from "@/lib/httpError";
import {
  addAutorToDocumento,
  createDocumentacion,
  getDocumentacionById,
  removeAutorFromDocumentacion,
  updateDocumentacion,
  type Autor,
} from "@/modules/produccion/services/documentacionServices";
import { getAutores, createAutor } from "@/modules/produccion/services/autoresService";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import { normalizarNombreAutor } from "@/modules/produccion/utils/documentacionAutores";

export default function DocumentacionForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { uct, uctGuard } = useUctGuard();
  const { user } = useAuth();
  const isEdit = Boolean(id);

  const { data: initial, isLoading } = useQuery({
    queryKey: ["documentacion", id],
    queryFn: () => (id ? getDocumentacionById(Number(id)) : null),
    enabled: isEdit,
  });

  const autoresQuery = useQuery({
    queryKey: ["autores"],
    queryFn: getAutores,
  });
  const autoresSistema = autoresQuery.data ?? [];
  const autoresNoDisponibles = autoresQuery.data === undefined;

  const [data, setData] = useState({
    titulo: "",
    editorial: "",
    fecha: "",
  });
  const [autores, setAutores] = useState<Autor[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!initial) return;

    setData({
      titulo: initial.titulo ?? "",
      editorial: initial.editorial ?? "",
      fecha: initial.fecha ?? "",
    });
    setAutores(initial.autores ?? []);
  }, [initial]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "produccion-documentacion",
    recordId: id,
    value: { data, autores },
    ready: !isEdit || (!isLoading && Boolean(initial)),
    autosave: false,
    hasContent: (draft) => Object.values(draft.data).some(Boolean) || draft.autores.some((autor) => autor.id > 0 || Boolean(autor.nombre_apellido.trim())),
    onRestore: (draft) => {
      setData(draft.data);
      setAutores(draft.autores.filter((autor) => autor.id > 0 || autor.nombre_apellido.trim()));
    },
  });

  const autoresDisponibles = useMemo(() => {
    const map = new Map<number, { id: number; nombre_apellido: string }>();

    for (const autor of autoresSistema) {
      map.set(autor.id, autor);
    }

    for (const autor of autores) {
      if (autor.id > 0) {
        map.set(autor.id, autor);
      }
    }

    return Array.from(map.values()).sort((a, b) =>
      a.nombre_apellido.localeCompare(b.nombre_apellido)
    );
  }, [autoresSistema, autores]);

  const clearError = (field: string) => {
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!data.titulo.trim()) newErrors.titulo = "Debe ingresar título";
    if (!data.editorial.trim()) newErrors.editorial = "Debe ingresar editorial";
    if (!data.fecha) newErrors.fecha = "Debe ingresar fecha";

    if (autores.length === 0) {
      newErrors.autores = "Debe añadir al menos un autor";
    }
    if (autores.some((autor) => autor.id <= 0 && !hasOnlyLettersAndSpaces(autor.nombre_apellido))) {
      newErrors.autores = "Use solo letras y espacios en el nombre de cada autor";
    }
    if (new Set(autores.map((autor) => normalizarNombreAutor(autor.nombre_apellido))).size !== autores.length) {
      newErrors.autores = "Quite los autores duplicados antes de guardar.";
    }
    if (autores.some((autor) => autor.id <= 0 && autoresSistema.some((existing) => normalizarNombreAutor(existing.nombre_apellido) === normalizarNombreAutor(autor.nombre_apellido)))) {
      newErrors.autores = "Seleccione los autores existentes desde la lista.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const { mutateAsync, isPending } = useMutation({
    mutationFn: async () => {
      if (!uct) {
        throw new Error("Grupo no disponible");
      }

      const persistedAutores: Autor[] = [];
      for (const autor of autores) {
        if (autor.id > 0) {
          persistedAutores.push(autor);
        } else {
          const creado = await createAutor(autor.nombre_apellido.trim());
          persistedAutores.push(creado);
        }
      }

      if (!isEdit) {
        const anio = new Date(`${data.fecha}T00:00:00`).getFullYear();

        const doc = await createDocumentacion({
          titulo: data.titulo.trim(),
          editorial: data.editorial.trim(),
          anio,
          fecha: data.fecha,
          grupo_id: uct.id,
        });

        for (const autor of persistedAutores) {
          await addAutorToDocumento(doc.id, autor.id);
        }

        return doc;
      }

      const initialPayload = {
        titulo: initial?.titulo ?? "",
        editorial: initial?.editorial ?? "",
        anio: initial?.anio ?? undefined,
        fecha: initial?.fecha ?? "",
        grupo_id: initial?.grupo_id ?? uct.id,
      };

      const anio = new Date(`${data.fecha}T00:00:00`).getFullYear();

      const payload = {
        titulo: data.titulo.trim(),
        editorial: data.editorial.trim(),
        anio,
        fecha: data.fecha,
        grupo_id: uct.id,
      };

      const changedPayload = Object.fromEntries(
        Object.entries(payload).filter(([key, value]) => {
          return initialPayload[key as keyof typeof initialPayload] !== value;
        })
      );

      const prevIds = initial?.autores?.map((autor) => autor.id) ?? [];
      const nextIds = persistedAutores.map((autor) => autor.id);
      const toAdd = nextIds.filter((autorId) => !prevIds.includes(autorId));
      const toRemove = prevIds.filter((autorId) => !nextIds.includes(autorId));

      if (
        Object.keys(changedPayload).length === 0 &&
        toAdd.length === 0 &&
        toRemove.length === 0
      ) {
        clearDraft();
        navigate(`/documentacion/${id}`, {
          replace: true,
          state: {
            successMessage: "No hubo cambios para actualizar.",
          },
        });
        return null;
      }

      let doc = initial;
      if (Object.keys(changedPayload).length > 0) {
        doc = await updateDocumentacion(Number(id), changedPayload);
      }

      for (const autorId of toAdd) {
        await addAutorToDocumento(Number(id), autorId);
      }

      for (const autorId of toRemove) {
        await removeAutorFromDocumentacion(Number(id), autorId);
      }

      return doc ?? initial ?? null;
    },
    onSuccess: async (saved) => {
      if (!saved) return;
      clearDraft();

      const documentacionId = isEdit ? Number(id) : saved.id;

      await qc.invalidateQueries({ queryKey: ["documentacion"] });
      await qc.invalidateQueries({ queryKey: ["autores"] });
      await qc.invalidateQueries({ queryKey: ["documentacion", documentacionId] });
      await qc.invalidateQueries({
        queryKey: ["documentacion-historial", documentacionId],
      });

      navigate(isEdit ? `/documentacion/${documentacionId}` : "/documentacion", {
        replace: true,
        state: {
          successMessage: isEdit
            ? "Documentación actualizada con éxito."
            : "Documentación creada con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["titulo","editorial","fecha","autores"])) return;
      setErrorMessage(
        getErrorMessage(
          error,
          isEdit
            ? "Lo sentimos, no pudimos actualizar la documentación. Revise los datos e intente nuevamente."
            : "Lo sentimos, no pudimos crear la documentación. Revise los datos e intente nuevamente."
        )
      );
      setShowError(true);
    },
  });

  if (isLoading) return <LoadingSkeleton variant="form" label="Cargando documentación..." />;

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar documentación" : "Nueva documentación"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={async (e) => {
          e.preventDefault();
          if (isPending || autoresNoDisponibles) return;
          if (!validate()) return;
          if (!uct) return;
          await mutateAsync();
        }}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Título" name="titulo" error={errors.titulo}>
          <>
            <input
              className={inputClass("titulo")}
              placeholder="Ingrese el título del documento"
              value={data.titulo}
              onChange={(e) => {
                setData((prev) => ({ ...prev, titulo: e.target.value }));
                if (e.target.value.trim()) clearError("titulo");
              }}
            />
          </>
        </Field>

        <Field required label="Autores" name="autores" error={errors.autores}>
          <>
            {autoresQuery.isError && <div className="mb-3 space-y-2"><p role="alert" className="text-sm text-rose-700">Lo sentimos, no pudimos recuperar los autores. Intente nuevamente.</p><Button type="button" variant="secondary" size="sm" loading={autoresQuery.isFetching} loadingText="Cargando autores..." onClick={() => { void autoresQuery.refetch(); }}>Reintentar</Button></div>}
            {autoresNoDisponibles && !autoresQuery.isError && <LoadingSkeleton variant="compact" label="Cargando autores..." />}
            {autoresQuery.data?.length === 0 && <p role="status" className="mb-3 text-sm text-slate-500">No hay autores registrados. Puede añadir uno nuevo.</p>}
            <DocumentacionAutoresField value={autores} options={autoresDisponibles}
              disabled={isPending || autoresNoDisponibles}
              onChange={(value) => { setAutores(value); if (value.length) clearError("autores"); }} />
          </>
        </Field>

        <Field required label="Editorial" name="editorial" error={errors.editorial}>
          <>
            <input
              className={inputClass("editorial")}
              placeholder="Ingrese la editorial"
              value={data.editorial}
              onChange={(e) => {
                setData((prev) => ({ ...prev, editorial: e.target.value }));
                if (e.target.value.trim()) clearError("editorial");
              }}
            />
          </>
        </Field>

        <Field required label="Fecha" name="fecha" error={errors.fecha}>
          <DatePicker
            value={data.fecha ? new Date(`${data.fecha}T00:00:00`) : null}
            onChange={(dt) => {
              setData((prev) => ({
                ...prev,
                fecha: toCivilDateString(dt) ?? "",
              }));
              if (dt) clearError("fecha");
            }}
            helperText="DD/MM/AAAA"
            className={inputClass("fecha")}
          />
        </Field>

        <div className="flex justify-between pt-6">
          <Button type="button" variant="secondary" size="sm" onClick={() => requestLeave(() => navigate(-1))}>
            Volver
          </Button>

          <Button type="submit" size="sm" disabled={isPending || autoresNoDisponibles} loading={isPending} loadingText="Guardando...">
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
