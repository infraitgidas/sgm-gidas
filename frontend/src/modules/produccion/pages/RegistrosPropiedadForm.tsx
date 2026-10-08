import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors } from "@/lib/httpError";
import { hasLetter } from "../../../lib/textValidation";
import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Button from "@/components/Button";
import DatePicker from "@/components/Calendar";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";
import { useTiposRegistroPropiedad } from "@/modules/produccion/hooks/useTipoRegistroPropiedad";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { getErrorMessage } from "@/lib/httpError";
import {
  createRegistroPropiedad,
  getRegistroPropiedadById,
  updateRegistroPropiedad,
  type RegistroPropiedad,
  type RegistroPropiedadPayload,
} from "@/modules/produccion/services/registrosPropiedadServices";
import { toTitleCase } from "@/utils/format";
import { parseCivilDate, toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";

export default function RegistrosPropiedadForm() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { uct, uctGuard } = useUctGuard();
  const { user } = useAuth();
  const { tipos = [] } = useTiposRegistroPropiedad();
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const registroId = id ? Number(id) : undefined;

  const { data: initial, isLoading } = useQuery({
    queryKey: ["registro-propiedad", registroId],
    queryFn: () => getRegistroPropiedadById(registroId as number),
    enabled: !!registroId,
  });

  const [data, setData] = useState({
    nombre_articulo: "",
    organismo_registrante: "",
    fecha_registro: "",
    tipo_registro_id: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!initial) {
      setData({
        nombre_articulo: "",
        organismo_registrante: "",
        fecha_registro: "",
        tipo_registro_id: "",
      });
      return;
    }

    setData({
      nombre_articulo: initial.nombre_articulo ?? "",
      organismo_registrante: initial.organismo_registrante ?? "",
      fecha_registro: initial.fecha_registro ?? "",
      tipo_registro_id: initial.tipo_registro_id?.toString() ?? "",
    });
  }, [initial]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "produccion-registros",
    recordId: id,
    value: data,
    ready: !isEdit || (!isLoading && Boolean(initial)),
    autosave: false,
    hasContent: (draft) => Object.values(draft).some(Boolean),
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

    if (!data.nombre_articulo.trim()) {
      newErrors.nombre_articulo = "Debe ingresar el nombre del artículo";
    } else if (!hasLetter(data.nombre_articulo)) {
      newErrors.nombre_articulo = "El nombre del artículo debe contener letras";
    }

    if (!data.organismo_registrante.trim()) {
      newErrors.organismo_registrante =
        "Debe ingresar el organismo registrante";
    }

    if (!data.fecha_registro) {
      newErrors.fecha_registro = "Debe seleccionar una fecha";
    }

    if (!data.tipo_registro_id) {
      newErrors.tipo_registro_id = "Debe seleccionar un tipo de registro";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const mutation = useMutation({
    mutationFn: (payload: Partial<RegistroPropiedadPayload>) =>
      isEdit
        ? updateRegistroPropiedad(registroId as number, payload)
        : createRegistroPropiedad(payload as RegistroPropiedadPayload),
    onSuccess: async (saved: RegistroPropiedad) => {
      clearDraft();
      await qc.invalidateQueries({ queryKey: ["registros-propiedad"] });
      await qc.invalidateQueries({ queryKey: ["registro-propiedad", registroId] });
      await qc.invalidateQueries({
        queryKey: ["registro-propiedad-historial", registroId],
      });

      const savedId = saved?.id ?? registroId;

      if (isEdit && savedId) {
        navigate(`/registros-propiedad/${savedId}`, {
          replace: true,
          state: {
            successMessage: "Registro actualizado con éxito.",
          },
        });
        return;
      }

      navigate("/registros-propiedad", {
        replace: true,
        state: {
          successMessage: "Registro creado con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["nombre_articulo","organismo_registrante","fecha_registro","tipo_registro_id"])) return;
      setErrorMessage(
        getErrorMessage(
          error,
          isEdit
            ? "Lo sentimos, no pudimos actualizar el registro de propiedad. Revise los datos e intente nuevamente."
            : "Lo sentimos, no pudimos crear el registro de propiedad. Revise los datos e intente nuevamente."
        )
      );

      setShowError(true);
    },
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mutation.isPending) return;

    if (!uct) return;
    if (!validate()) return;

    const payload = {
      nombre_articulo: toTitleCase(data.nombre_articulo.trim()),
      organismo_registrante: toTitleCase(data.organismo_registrante.trim()),
      fecha_registro: data.fecha_registro,
      tipo_registro_id: Number(data.tipo_registro_id),
      grupo_utn_id: uct.id,
    };

    if (!isEdit) {
      await mutation.mutateAsync(payload);
      return;
    }

    const initialPayload = {
      nombre_articulo: initial?.nombre_articulo ?? "",
      organismo_registrante: initial?.organismo_registrante ?? "",
      fecha_registro: initial?.fecha_registro ?? "",
      tipo_registro_id: initial?.tipo_registro_id ?? null,
      grupo_utn_id: initial?.grupo_utn_id ?? uct.id,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    if (Object.keys(changedPayload).length === 0) {
      clearDraft();
      navigate(`/registros-propiedad/${registroId}`, {
        replace: true,
        state: {
          successMessage: "No hubo cambios para actualizar.",
        },
      });
      return;
    }

    await mutation.mutateAsync(changedPayload);
  };

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  if (isEdit && isLoading) {
    return <LoadingSkeleton variant="form" label="Cargando..." />;
  }

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar registro" : "Nuevo registro"}
      </h2>

      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Nombre del artículo" name="nombre_articulo" error={errors.nombre_articulo}>
          <>
            <input
              className={inputClass("nombre_articulo")}
              placeholder="Ej: Sistema de monitoreo inteligente"
              value={data.nombre_articulo}
              onChange={(e) => {
                setData({
                  ...data,
                  nombre_articulo: e.target.value,
                });
                if (e.target.value.trim()) clearError("nombre_articulo");
              }}
              onBlur={() =>
                setData({
                  ...data,
                  nombre_articulo: toTitleCase(data.nombre_articulo),
                })
              }
            />
            {errors.nombre_articulo && (
              <p className="mt-1 text-sm text-red-500">
                {errors.nombre_articulo}
              </p>
            )}
          </>
        </Field>

        <Field required label="Organismo registrante" name="organismo_registrante" error={errors.organismo_registrante}>
          <>
            <input
              className={inputClass("organismo_registrante")}
              placeholder="Ej: INPI"
              value={data.organismo_registrante}
              onChange={(e) => {
                setData({
                  ...data,
                  organismo_registrante: e.target.value,
                });
                if (e.target.value.trim()) {
                  clearError("organismo_registrante");
                }
              }}
              onBlur={() =>
                setData({
                  ...data,
                  organismo_registrante: toTitleCase(
                    data.organismo_registrante
                  ),
                })
              }
            />
            {errors.organismo_registrante && (
              <p className="mt-1 text-sm text-red-500">
                {errors.organismo_registrante}
              </p>
            )}
          </>
        </Field>

        <Field required label="Fecha de registro" name="fecha_registro" error={errors.fecha_registro}>
          <DatePicker
            value={parseCivilDate(data.fecha_registro)}
            onChange={(dt) => {
              setData({
                ...data,
                fecha_registro: toCivilDateString(dt) ?? "",
              });
              if (dt) clearError("fecha_registro");
            }}
            helperText="DD/MM/AAAA"
            className={inputClass("fecha_registro")}
          />
        </Field>

        <Field required label="Tipo de registro" name="tipo_registro_id" error={errors.tipo_registro_id}>
          <>
            <select
              className={`${inputClass("tipo_registro_id")} ${
                !data.tipo_registro_id ? "text-slate-400" : "text-slate-900"
              }`}
              value={data.tipo_registro_id}
              onChange={(e) => {
                setData({
                  ...data,
                  tipo_registro_id: e.target.value,
                });
                if (e.target.value) clearError("tipo_registro_id");
              }}
            >
              <option value="" disabled>
                Seleccionar tipo
              </option>

              {tipos.map((tipo) => (
                <option key={tipo.id} value={tipo.id}>
                  {tipo.nombre}
                </option>
              ))}
            </select>

            {errors.tipo_registro_id && (
              <p className="mt-1 text-sm text-red-500">
                {errors.tipo_registro_id}
              </p>
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

          <Button type="submit" size="sm" disabled={mutation.isPending} loading={mutation.isPending} loadingText="Guardando...">
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
