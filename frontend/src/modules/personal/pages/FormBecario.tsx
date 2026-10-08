import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { hasOnlyLettersAndSpaces } from "../../../lib/textValidation";
import { LoaderCircle } from "lucide-react";
import { useState, useEffect } from "react";
import { MAX_HORAS_SEMANALES, validWeeklyHours, WEEKLY_HOURS_ERROR } from "@/modules/personal/utils/weeklyHours";
import { personalFieldErrors } from "@/modules/personal/utils/personalFieldErrors";
import { validateDni, validateCuil } from "@/modules/personal/utils/identidadValidation";
import IdentidadFields from "@/modules/personal/components/IdentidadFields";
import { useNavigate } from "react-router-dom";
import Button from "@/components/Button";
import Field from "@/components/Field";
import { useUct } from "@/modules/grupo/hooks/useUct";
import { useTiposFormacion } from "@/modules/personal/hooks/useTiposFormacion";
import {
  crearBecario,
  actualizarBecario,
} from "@/modules/personal/services/becarioServices";
import type { PersonalCompleto } from "@/modules/personal/services/personalCompletoServices";
import { useQueryClient } from "@tanstack/react-query";
import { useBecas } from "@/modules/recursos/hooks/useBecas";
import Calendar from "@/components/Calendar";
import { useAuth } from "@/context/AuthContext";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import { toCivilDateString } from "@/utils/dateTime";

interface Props {
  initialData?: PersonalCompleto;
  onCancel: () => void;
  onError: (error: unknown) => void;
}

type BecaVinculada = {
  idLocal: string;
  becaId: number | "";
  fechaInicio: Date | null;
  fechaFin: Date | null;
  monto: number | "";
};

export default function FormBecario({ initialData, onCancel, onError }: Props) {
  const navigate = useNavigate();
  const { uct } = useUct();
  const { data: tiposFormacion = [] } = useTiposFormacion();
  const qc = useQueryClient();
  const { data: becasLista = [] } = useBecas();

  const isEdit = Boolean(initialData);
  const { user } = useAuth();

  const [nombreApellido, setNombre] = useState("");
  const [dni, setDni] = useState("");
  const [cuil, setCuil] = useState("");
  const [horasSemanales, setHoras] = useState<number | "">("");
  const [tipoFormacionId, setTipoFormacionId] = useState<number | "">("");
  const [fechaAltaGrupo, setFechaAltaGrupo] = useState<Date | null>(null);
  const [activo, setActivo] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [agregarBeca, setAgregarBeca] = useState(false);

  const createEmptyBeca = (): BecaVinculada => ({
    idLocal: Math.random().toString(36).slice(2, 11),
    becaId: "",
    fechaInicio: null,
    fechaFin: null,
    monto: "",
  });

  const [becasVinculadas, setBecasVinculadas] = useState<BecaVinculada[]>([]);
  const [becasPage, setBecasPage] = useState(1);
  const [isSaving, setIsSaving] = useState(false);
  const [hydrated, setHydrated] = useState(!isEdit);
  const [becasSearch, setBecasSearch] = useState("");
  const filteredBecas = becasVinculadas.map((beca, index) => ({ beca, index })).filter(({ beca }) => {
    const name = becasLista.find((option) => option.id === beca.becaId)?.nombre_beca ?? "sin seleccionar";
    const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es").trim();
    return normalize(name).includes(normalize(becasSearch));
  });
  const currentBecasPage = Math.min(becasPage, Math.max(1, Math.ceil(filteredBecas.length / 5)));

  const formatDateStr = (d: Date | null) => {
    if (!d) return undefined;
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${dd}`;
  };

  useEffect(() => {
    if (!initialData) {
      setNombre("");
      setDni("");
      setCuil("");
      setHoras("");
      setTipoFormacionId("");
      setFechaAltaGrupo(null);
      setActivo(true);
      setAgregarBeca(false);
      setBecasVinculadas([]);
      return;
    }

    setNombre(initialData.nombre_apellido ?? "");
    setDni(initialData.dni ?? "");
    setCuil(initialData.cuil ?? "");
    setHoras(initialData.horas_semanales ?? "");
    setActivo(initialData.activo ?? true);
    setFechaAltaGrupo(
      initialData.fecha_alta_grupo
        ? new Date(`${initialData.fecha_alta_grupo}T00:00:00`)
        : null
    );
    setTipoFormacionId(
      initialData.relaciones?.tipo_formacion?.id ??
        initialData.tipo_formacion_id ??
        ""
    );

    if (initialData.becas && initialData.becas.length > 0) {
      setAgregarBeca(true);
      setBecasVinculadas(
        initialData.becas.map((b) => ({
          idLocal: Math.random().toString(36).slice(2, 11),
          becaId: b.id ?? "",
          fechaInicio: b.fecha_inicio
            ? new Date(`${b.fecha_inicio}T00:00:00`)
            : null,
          fechaFin: b.fecha_fin
            ? new Date(`${b.fecha_fin}T00:00:00`)
            : null,
          monto:
            b.monto_percibido !== null && b.monto_percibido !== undefined
              ? b.monto_percibido
              : "",
        }))
      );
    } else {
      setAgregarBeca(false);
      setBecasVinculadas([]);
    }
    setHydrated(true);
  }, [initialData]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "personal-becario",
    recordId: initialData?.id,
    value: {
      nombreApellido, dni, cuil, horasSemanales, tipoFormacionId, fechaAltaGrupo: toCivilDateString(fechaAltaGrupo), activo, agregarBeca,
      becasVinculadas: becasVinculadas.map((beca) => ({ ...beca, fechaInicio: toCivilDateString(beca.fechaInicio), fechaFin: toCivilDateString(beca.fechaFin) })),
    },
    ready: hydrated,
    autosave: false,
    hasContent: (draft) => Boolean(draft.nombreApellido || draft.dni || draft.cuil || draft.horasSemanales || draft.tipoFormacionId || draft.fechaAltaGrupo || draft.becasVinculadas.length),
    onRestore: (draft) => {
      setNombre(draft.nombreApellido); setDni(draft.dni ?? ""); setCuil(draft.cuil ?? ""); setHoras(draft.horasSemanales); setTipoFormacionId(draft.tipoFormacionId);
      setFechaAltaGrupo(draft.fechaAltaGrupo ? new Date(`${draft.fechaAltaGrupo}T00:00:00`) : null);
      setActivo(draft.activo); setAgregarBeca(draft.agregarBeca);
      setBecasVinculadas(draft.becasVinculadas.map((beca) => ({
        ...beca,
        fechaInicio: beca.fechaInicio ? new Date(`${beca.fechaInicio}T00:00:00`) : null,
        fechaFin: beca.fechaFin ? new Date(`${beca.fechaFin}T00:00:00`) : null,
      })));
    },
  });

  const normalizedBecas = becasVinculadas.map((beca) => ({
    beca_id: Number(beca.becaId),
    fecha_inicio: formatDateStr(beca.fechaInicio) ?? "",
    fecha_fin: formatDateStr(beca.fechaFin),
    monto_percibido: beca.monto !== "" ? Number(beca.monto) : undefined,
  }));

  const hasUnsavedChanges = () => {
    if (!initialData) return true;
    const originalBecas = (initialData.becas ?? []).map((beca) => ({
      beca_id: Number(beca.id),
      fecha_inicio: beca.fecha_inicio,
      fecha_fin: beca.fecha_fin || undefined,
      monto_percibido: beca.monto_percibido ?? undefined,
    }));
    return nombreApellido !== (initialData.nombre_apellido ?? "") ||
      dni !== (initialData.dni ?? "") || cuil !== (initialData.cuil ?? "") ||
      Number(horasSemanales) !== Number(initialData.horas_semanales) ||
      Number(tipoFormacionId) !== Number(initialData.relaciones?.tipo_formacion?.id ?? initialData.tipo_formacion_id) ||
      toCivilDateString(fechaAltaGrupo) !== (initialData.fecha_alta_grupo ?? "") ||
      activo !== (initialData.activo ?? true) ||
      agregarBeca !== (originalBecas.length > 0) ||
      JSON.stringify(normalizedBecas) !== JSON.stringify(originalBecas);
  };

  const handleCancel = () => {
    if (isEdit && !availableDraft && !hasUnsavedChanges()) {
      clearDraft();
      onCancel();
      return;
    }
    requestLeave(onCancel);
  };

  const clearError = (field: string) => {
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  const clearBecaErrors = () => {
    setErrors((prev) => {
      const copy = { ...prev };
      Object.keys(copy).forEach((key) => {
        if (key.startsWith("beca")) delete copy[key];
      });
      return copy;
    });
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!nombreApellido.trim()) {
      newErrors.nombre = "Debe ingresar nombre y apellido";
    } else if (!hasOnlyLettersAndSpaces(nombreApellido)) {
      newErrors.nombre = "Use solo letras y espacios en nombre y apellido";
    }

    const dniError = validateDni(dni);
    if (dniError) newErrors.dni = dniError;
    const cuilError = validateCuil(cuil, dni);
    if (cuilError) newErrors.cuil = cuilError;

    if (!validWeeklyHours(horasSemanales)) {
      newErrors.horas = WEEKLY_HOURS_ERROR;
    }

    if (!tipoFormacionId) {
      newErrors.tipoFormacion = "Debe seleccionar tipo de formación";
    }

    if (!fechaAltaGrupo) {
      newErrors.fechaAltaGrupo = "Debe ingresar la fecha de alta en el grupo";
    }
    if (!uct?.id) newErrors.grupo = "Lo sentimos, no pudimos recuperar el grupo. Intente nuevamente.";

    if (agregarBeca) {
      if (becasVinculadas.length === 0) {
        newErrors.becaGlobal = "Debe agregar al menos una beca";
      } else {
        becasVinculadas.forEach((beca, index) => {
          if (!beca.becaId) {
            newErrors[`beca_${index}_id`] =
              "Debe seleccionar un tipo de beca";
          }
          if (!beca.fechaInicio) {
            newErrors[`beca_${index}_fechaInicio`] =
              "Debe ingresar una fecha de inicio";
          }
          if (!beca.fechaFin) {
            newErrors[`beca_${index}_fechaFin`] = "Debe ingresar una fecha de fin";
          } else if (beca.fechaInicio && beca.fechaFin < beca.fechaInicio) {
            newErrors[`beca_${index}_fechaFin`] = "La fecha de fin debe ser igual o posterior al inicio";
          }
        });
      }
    }

    setErrors(newErrors);
    if (Object.keys(newErrors).length) {
      const firstBecaError = Object.keys(newErrors).find((key) => /^beca_\d+_/.test(key));
      if (firstBecaError) {
        setBecasSearch("");
        setBecasPage(Math.floor(Number(firstBecaError.split("_")[1]) / 5) + 1);
      }
      focusFieldErrors(newErrors);
      onError(new Error("No pudimos guardar el registro. Complete o corrija los campos indicados e intente nuevamente."));
    }
    return Object.keys(newErrors).length === 0;
  };

  const executeSafely = async (operation: () => Promise<unknown>) => {
    try {
      await operation();
      return true;
    } catch (error) {
      onError(error);
      if (applyFieldErrors(error, setErrors, ["nombre","dni","cuil","horas","tipoFormacion","fechaAltaGrupo","becaGlobal"])) return false;
      const fieldErrors = personalFieldErrors(error);
      if (fieldErrors.horas) {
        setErrors((prev) => ({ ...prev, horas: fieldErrors.horas }));
        document.getElementById("becario-horas")?.focus();
      }
      return false;
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSaving) return;
    if (!validate()) return;
    setIsSaving(true);
    try {

      const payload = {
        nombre_apellido: nombreApellido,
        dni,
        cuil,
        horas_semanales: Number(horasSemanales),
        tipo_formacion_id: Number(tipoFormacionId),
        fecha_alta_grupo: formatDateStr(fechaAltaGrupo)!,
        grupo_utn_id: uct!.id,
        activo,
        becas: agregarBeca
          ? becasVinculadas.map((beca) => ({
              beca_id: Number(beca.becaId),
              fecha_inicio: formatDateStr(beca.fechaInicio)!,
              fecha_fin: formatDateStr(beca.fechaFin),
              monto_percibido: beca.monto !== "" ? Number(beca.monto) : undefined,
            }))
          : [],
      };

      if (isEdit && initialData?.id) {
        const original = {
          nombre_apellido: initialData.nombre_apellido,
          dni: initialData.dni ?? "",
          cuil: initialData.cuil ?? "",
          horas_semanales: Number(initialData.horas_semanales),
          tipo_formacion_id: Number(initialData.relaciones?.tipo_formacion?.id ?? initialData.tipo_formacion_id),
          fecha_alta_grupo: initialData.fecha_alta_grupo,
          grupo_utn_id: Number(initialData.grupo_utn_id ?? uct!.id),
          activo: initialData.activo ?? true,
          becas: (initialData.becas || []).map((beca) => ({
            beca_id: Number(beca.id),
            fecha_inicio: beca.fecha_inicio,
            fecha_fin: beca.fecha_fin || undefined,
            monto_percibido: beca.monto_percibido ?? undefined,
          })),
        };
        const changedPayload = Object.fromEntries(
          Object.entries(payload).filter(([key, value]) =>
            JSON.stringify(value) !== JSON.stringify(original[key as keyof typeof original])
          )
        );
        if (Object.keys(changedPayload).length > 0) {
          const updated = await executeSafely(() =>
            actualizarBecario(initialData.id, changedPayload)
          );
          if (!updated) return;
        }

        await qc.invalidateQueries({ queryKey: ["personal"] });
        await qc.invalidateQueries({ queryKey: ["becarios"] });
        await qc.invalidateQueries({
          queryKey: ["personal-detalle", "becario", String(initialData.id)],
        });

        clearDraft();
        navigate(`/personal/becario/${initialData.id}`, {
          replace: true,
          state: { successMessage: "¡Actualizado con éxito!" },
        });

        return;
      }

      const created = await executeSafely(() => crearBecario(payload));
      if (!created) return;

      await qc.invalidateQueries({ queryKey: ["personal"] });
      await qc.invalidateQueries({ queryKey: ["becarios"] });

      clearDraft();
      navigate("/personal", {
        state: { successMessage: "¡Creado con éxito!" },
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form
      noValidate
      onSubmit={submit}
      className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
    >
      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      {errors.grupo && <p role="alert">{errors.grupo}</p>}
      <Field required label="Nombre y apellido" name="nombre" error={errors.nombre}>
        <>
          <input
            className={`input ${
              errors.nombre ? "!border-red-500 !ring-2 !ring-red-500" : ""
            }`}
            value={nombreApellido}
            onChange={(e) => {
              setNombre(e.target.value);
              if (e.target.value.trim()) clearError("nombre");
            }}
          />
          {errors.nombre && (
            <p className="mt-1 text-sm text-red-500">{errors.nombre}</p>
          )}
        </>
      </Field>

      <IdentidadFields prefix="becario" dni={dni} cuil={cuil} errors={errors}
        onDniChange={(value) => { setDni(value); clearError("dni"); clearError("cuil"); }}
        onCuilChange={(value) => { setCuil(value); clearError("cuil"); }} />

      <Field required label="Horas semanales" name="horas" error={errors.horas}>
        <>
          <input
            type="number"
            min="1"
            max={MAX_HORAS_SEMANALES}
            step="1"
            aria-label="Horas semanales"
            id="becario-horas"
            aria-describedby={errors.horas ? "becario-horas-error" : undefined}
            aria-invalid={Boolean(errors.horas)}
            className={`input ${
              errors.horas ? "!border-red-500 !ring-2 !ring-red-500" : ""
            }`}
            value={horasSemanales}
            onChange={(e) => {
              const value = e.target.value === "" ? "" : +e.target.value;
              setHoras(value);
              if (validWeeklyHours(value)) clearError("horas");
            }}
          />
          {errors.horas && (
            <p id="becario-horas-error" role="alert" className="mt-1 text-sm text-red-500">{errors.horas}</p>
          )}
        </>
      </Field>

      <Field required label="Tipo de formación" name="tipoFormacion" error={errors.tipoFormacion}>
        <>
          <select
            className={`input ${
              errors.tipoFormacion ? "!border-red-500 !ring-2 !ring-red-500" : ""
            } ${!tipoFormacionId ? "text-slate-400" : "text-slate-900"}`}
            value={tipoFormacionId}
            onChange={(e) => {
              const value = e.target.value ? +e.target.value : "";
              setTipoFormacionId(value);
              if (value) clearError("tipoFormacion");
            }}
          >
            <option value="" disabled>
              Seleccionar tipo de formación
            </option>
            {tiposFormacion.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre}
              </option>
            ))}
          </select>
          {errors.tipoFormacion && (
            <p className="mt-1 text-sm text-red-500">
              {errors.tipoFormacion}
            </p>
          )}
        </>
      </Field>

      <Field required label="Fecha de alta en el grupo" name="fechaAltaGrupo" error={errors.fechaAltaGrupo}>
        <Calendar
          value={fechaAltaGrupo}
          onChange={(date) => {
            setFechaAltaGrupo(date);
            if (date) clearError("fechaAltaGrupo");
          }}
          className={`input ${
            errors.fechaAltaGrupo ? "!border-red-500 !ring-2 !ring-red-500" : ""
          }`}
          helperText="DD/MM/AAAA"
        />
      </Field>

      <div className="space-y-6 rounded-lg border border-slate-200 bg-slate-50 p-6">
        <div className="flex flex-col gap-3 border-b border-slate-200 pb-4">
          <h4 className="font-semibold text-slate-800">Becas</h4>

          <p className="text-sm text-slate-600">
            Si el becario no percibe una beca, deja esta sección sin seleccionar.
            Seleccione una beca existente y registre el plazo de la vinculación.
          </p>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="checkbox-agregar-beca"
              aria-invalid={Boolean(errors.becaGlobal)}
              aria-describedby={errors.becaGlobal ? "becario-beca-global-error" : undefined}
              checked={agregarBeca}
              onChange={(e) => {
                const isChecked = e.target.checked;
                setAgregarBeca(isChecked);

                if (!isChecked) {
                  setBecasVinculadas([]);
                  clearBecaErrors();
                } else {
                  if (becasVinculadas.length === 0) {
                    setBecasVinculadas([createEmptyBeca()]);
                  }
                  clearError("becaGlobal");
                }
              }}
              className="h-4 w-4 cursor-pointer rounded border-slate-300 accent-slate-700"
            />
            <label
              htmlFor="checkbox-agregar-beca"
              className="cursor-pointer text-sm font-medium text-slate-700"
            >
              Vincular beca existente
            </label>
          </div>

          {errors.becaGlobal && (
            <p id="becario-beca-global-error" role="alert" className="mt-1 text-xs text-red-500">{errors.becaGlobal}</p>
          )}
        </div>

        {agregarBeca && (
          <div className="space-y-6">
            {becasLista.length === 0 && <p role="status" className="text-sm text-slate-600">No hay becas disponibles. Puede registrarlas desde Personal &gt; Becas.</p>}
            <div>
              <label htmlFor="becas-search" className="mb-1 block text-sm">Buscar becas vinculadas</label>
              <input id="becas-search" type="search" className="input w-full" value={becasSearch} placeholder="Tipo de beca" onChange={(event) => { setBecasSearch(event.target.value); setBecasPage(1); }} onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }} />
            </div>
            <p role="status" className="text-xs text-slate-500">
              {filteredBecas.length
                ? `Mostrando ${(currentBecasPage - 1) * 5 + 1} a ${Math.min(currentBecasPage * 5, filteredBecas.length)} de ${filteredBecas.length} becas vinculadas.`
                : "No hay coincidencias. Pruebe otro tipo de beca."}
            </p>
            {filteredBecas.slice((currentBecasPage - 1) * 5, currentBecasPage * 5).map(({ beca, index }) => {
              return (
              <div
                key={beca.idLocal}
                className="group relative rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
              >
                {becasVinculadas.length > 1 && (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="absolute right-2 top-2 bg-white px-3 py-1 text-xs text-red-500 hover:text-red-700"
                    title="Eliminar esta beca"
                    onClick={() => {
                      setBecasVinculadas((prev) =>
                        prev.filter((_, i) => i !== index)
                      );
                    }}
                  >
                    x
                  </Button>
                )}

                <h5 className="mb-3 text-xs font-semibold uppercase text-slate-500">
                  Beca #{index + 1}
                </h5>

                <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-2">
                  <Field required label="Tipo de beca" name={`beca_${index}_id`} error={errors[`beca_${index}_id`]}>
                    <>
                      <select
                        className={`input py-2 text-sm text-slate-900 ${
                          errors[`beca_${index}_id`]
                            ? "!border-red-500 !ring-2 !ring-red-500"
                            : ""
                        }`}
                        value={beca.becaId}
                        onChange={(e) => {
                          const val =
                            e.target.value === "" ? "" : Number(e.target.value);

                          setBecasVinculadas((prev) => {
                            const next = [...prev];
                            next[index].becaId = val;
                            return next;
                          });

                          if (val !== "") clearError(`beca_${index}_id`);
                        }}
                      >
                        <option value="" disabled>
                          Seleccionar beca existente
                        </option>
                        {becasLista.map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.nombre_beca}
                          </option>
                        ))}
                      </select>
                      {errors[`beca_${index}_id`] && (
                        <p className="mt-1 text-xs text-red-500">
                          {errors[`beca_${index}_id`]}
                        </p>
                      )}
                    </>
                  </Field>

                  <Field label="Monto percibido (Opcional)">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Ej. 150000"
                      className="input py-2 text-sm"
                      value={beca.monto}
                      onChange={(e) => {
                        const val = e.target.value === "" ? "" : +e.target.value;

                        setBecasVinculadas((prev) => {
                          const next = [...prev];
                          next[index].monto = val;
                          return next;
                        });
                      }}
                    />
                  </Field>

                  <Field required label="Fecha inicio" name={`beca_${index}_fechaInicio`} error={errors[`beca_${index}_fechaInicio`]}>
                    <Calendar
                      value={beca.fechaInicio}
                      onChange={(date) => {
                        setBecasVinculadas((prev) => {
                          const next = [...prev];
                          next[index].fechaInicio = date;
                          return next;
                        });
                        if (date) clearError(`beca_${index}_fechaInicio`);
                      }}
                      className={`input py-2 text-sm ${
                        errors[`beca_${index}_fechaInicio`]
                          ? "!border-red-500 !ring-2 !ring-red-500"
                          : ""
                      }`}
                      helperText="DD/MM/AAAA"
                    />
                  </Field>

                  <Field required label="Fecha fin" name={`beca_${index}_fechaFin`} error={errors[`beca_${index}_fechaFin`]}>
                    <Calendar
                      value={beca.fechaFin}
                      onChange={(date) => {
                        setBecasVinculadas((prev) => {
                          const next = [...prev];
                          next[index].fechaFin = date;
                          return next;
                        });
                        if (date) clearError(`beca_${index}_fechaFin`);
                      }}
                      minDate={beca.fechaInicio ?? undefined}
                      className={`input py-2 text-sm ${errors[`beca_${index}_fechaFin`] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`}
                      helperText="DD/MM/AAAA"
                    />
                  </Field>
                </div>
              </div>
              );
            })}

            {filteredBecas.length > 5 && <nav aria-label="Páginas de becas vinculadas" className="flex items-center gap-2 text-sm">
              <Button type="button" variant="secondary" size="sm" disabled={currentBecasPage === 1} onClick={() => setBecasPage(currentBecasPage - 1)}>Anterior</Button>
              <span role="status">Página {currentBecasPage} de {Math.ceil(filteredBecas.length / 5)}</span>
              <Button type="button" variant="secondary" size="sm" disabled={currentBecasPage === Math.ceil(filteredBecas.length / 5)} onClick={() => setBecasPage(currentBecasPage + 1)}>Siguiente</Button>
            </nav>}

            <div className="flex pt-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  setBecasVinculadas((prev) => [...prev, createEmptyBeca()]);
                  setBecasSearch("");
                  setBecasPage(Math.ceil((becasVinculadas.length + 1) / 5));
                }}
                className="px-3 py-1 text-xs"
              >
                + Vincular otra beca
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between pt-6">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleCancel}
        >
          Volver
        </Button>

        <Button type="submit" size="sm" disabled={isSaving} aria-busy={isSaving} loading={isSaving} loadingText="Guardando...">
          {isSaving && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />}
          {isSaving ? "Guardando..." : isEdit ? "Actualizar" : "Guardar"}
        </Button>
      </div>
    <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />
    </form>
  );
}
