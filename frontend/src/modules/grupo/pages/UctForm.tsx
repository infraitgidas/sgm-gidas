import { applyFieldErrors, focusFieldErrors, getApiFieldErrors } from "@/lib/httpError";
import { hasLetter, hasOnlyLettersAndSpaces } from "../../../lib/textValidation";
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Pencil, X } from "lucide-react";
import Button from "@/components/Button";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ConfirmDialog from "@/components/ConfirmDialog";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import Field from "@/components/Field";
import ErrorText from "@/components/ErrorText";
import { getErrorMessage } from "@/lib/httpError";
import { useUct } from "@/modules/grupo/hooks/useUct";
import { useCargos } from "@/modules/grupo/hooks/useCargos";
import {
  useCrearYAsignarDirectivo,
  useActualizarDirectivo,
  useDirectivos,
  useFinalizarDirectivo,
} from "@/modules/grupo/hooks/useDirectivos";
import {
  normalizarCargoDirectivo,
  obtenerCargosDirectivosFaltantes,
} from "@/modules/grupo/utils/directivoCargo";
import { useAuth } from "@/context/AuthContext";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import {
  getLocalTodayIso,
  INSTITUTIONAL_MIN_DATE_ISO,
  isInstitutionalDate,
} from "@/utils/dateTime";

type DirectivoItem = {
  id?: number;
  id_directivo?: number;
  nombre_apellido: string;
  cargo: string;
  fecha_inicio?: string;
  fecha_fin?: string | null;
};

export default function UctForm() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitInFlight = useRef(false);
  const hasStartedSave = useRef(false);
  const createdDirectivoSlots = useRef(new Set<1 | 2>());
  const todayIso = getLocalTodayIso();
  const { uct, save, isLoading: isLoadingUct } = useUct();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const isEdit = !!uct;
  const grupoId = uct?.id;

  useEffect(() => {
    if (isLoadingUct || hasStartedSave.current) return;
    if (isEdit && location.pathname === "/uct/nueva") {
      navigate("/uct/editar", { replace: true });
    } else if (!isEdit && location.pathname === "/uct/editar") {
      navigate("/uct/nueva", { replace: true });
    }
  }, [isEdit, isLoadingUct, location.pathname, navigate]);

  const { data: cargos = [], isLoading: isLoadingCargos } = useCargos();
  const {
    data: directivosActuales = [],
    isLoading: isLoadingDirectivos,
  } = useDirectivos(grupoId, !hasStartedSave.current);
  const crearAsignar = useCrearYAsignarDirectivo(grupoId ?? 0);
  const actualizarDirectivo = useActualizarDirectivo(grupoId);
  const finalizarDirectivo = useFinalizarDirectivo(grupoId);

  const [data, setData] = useState({
    facultadRegional: "",
    nombreSigla: "",
    nombre1: "",
    cargo1: "",
    fecha1: "",
    nombre2: "",
    cargo2: "",
    fecha2: "",
    correo: "",
    objetivos: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingNombre, setEditingNombre] = useState("");

  const [mostrarAltaDirectivos, setMostrarAltaDirectivos] = useState(false);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [fechaFin, setFechaFin] = useState("");
  const [directivoAFinalizar, setDirectivoAFinalizar] =
    useState<DirectivoItem | null>(null);

  const [submitError, setSubmitError] = useState("");
  const [pendingUpdates, setPendingUpdates] = useState<Record<number, string>>({});
  const [pendingFinalizations, setPendingFinalizations] = useState<Record<number, string>>({});
  const [formInitialized, setFormInitialized] = useState(false);

  const cargosFaltantes = obtenerCargosDirectivosFaltantes(directivosActuales);
  const faltaDirector =
    isEdit && !isLoadingDirectivos && cargosFaltantes.includes("Director");
  const faltaVicedirector =
    isEdit && !isLoadingDirectivos && cargosFaltantes.includes("Vicedirector");
  const tieneDirectivos = directivosActuales.length > 0;

  const cargoDirector = cargos.find(
    (c) => normalizarCargoDirectivo(c.nombre) === "director"
  );

  const cargoVicedirector = cargos.find(
    (c) => normalizarCargoDirectivo(c.nombre) === "vicedirector"
  );

  useEffect(() => {
    if (isLoadingUct || isLoadingCargos) return;

    setData((prev) => ({
      ...prev,
      facultadRegional: uct?.facultadRegional ?? "",
      nombreSigla: uct?.nombreSigla ?? "",
      correo: uct?.correo ?? "",
      objetivos: uct?.objetivos ?? "",
      nombre1: "",
      fecha1: "",
      cargo1: cargoDirector ? String(cargoDirector.id) : "",
      nombre2: "",
      fecha2: "",
      cargo2: cargoVicedirector ? String(cargoVicedirector.id) : "",
    }));
    setFormInitialized(true);
  }, [uct, cargoDirector, cargoVicedirector, isLoadingCargos, isLoadingUct]);

  const draftValue = {
    data,
    pendingUpdates,
    pendingFinalizations,
    mostrarAltaDirectivos,
  };
  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "grupo-uct",
    recordId: grupoId,
    value: draftValue,
    ready: formInitialized,
    autosave: false,
    hasContent: (draft) => Boolean(
      draft.data.facultadRegional || draft.data.nombreSigla || draft.data.correo ||
      draft.data.objetivos || draft.data.nombre1 || draft.data.nombre2 ||
      Object.keys(draft.pendingUpdates).length ||
      Object.keys(draft.pendingFinalizations).length
    ),
    onRestore: (draft) => {
      setData(draft.data);
      setPendingUpdates(draft.pendingUpdates);
      setPendingFinalizations(draft.pendingFinalizations);
      setMostrarAltaDirectivos(draft.mostrarAltaDirectivos);
    },
  });

  useEffect(() => {
    if (!faltaDirector && !faltaVicedirector) {
      setMostrarAltaDirectivos(false);
    }
  }, [faltaDirector, faltaVicedirector]);

  const change =
    (k: string) =>
    (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      >
    ) => {
      const value = e.target.value;
      setData((d) => ({ ...d, [k]: value }));

      setErrors((prev) => {
        const copy = { ...prev };
        delete copy[k];
        return copy;
      });
    };

  const validate = () => {
    const e: Record<string, string> = {};

    if (!data.facultadRegional.trim()) {
      e.facultadRegional = "Debe ingresar facultad regional";
    } else if (!hasLetter(data.facultadRegional)) {
      e.facultadRegional = "La facultad regional debe contener letras";
    }

    if (!data.nombreSigla.trim()) {
      e.nombreSigla = "Debe ingresar nombre y sigla";
    } else if (!hasLetter(data.nombreSigla)) {
      e.nombreSigla = "El nombre y sigla debe contener letras";
    }

    if (!data.correo.trim()) {
      e.correo = "Debe ingresar correo";
    } else if (!/^\S+@\S+\.\S+$/.test(data.correo)) {
      e.correo = "Formato de correo inválido";
    }

    if (!data.objetivos.trim()) {
      e.objetivos = "Debe ingresar objetivos";
    }

    if (mostrarAltaDirectivos && faltaDirector) {
      if (!data.nombre1.trim()) {
        e.nombre1 = "Ingrese nombre";
      } else if (!hasOnlyLettersAndSpaces(data.nombre1)) {
        e.nombre1 = "Use solo letras y espacios";
      }
      if (!data.cargo1) {
        e.cargo1 = "Seleccione cargo";
      }
      if (!data.fecha1) {
        e.fecha1 = "Ingrese fecha";
      } else if (!isInstitutionalDate(data.fecha1)) {
        e.fecha1 = "La fecha debe ser igual o posterior al 01/01/2010";
      } else if (data.fecha1 > todayIso) {
        e.fecha1 = "La fecha no puede ser futura";
      }
    }

    if (mostrarAltaDirectivos && faltaVicedirector) {
      if (!data.nombre2.trim()) {
        e.nombre2 = "Ingrese nombre";
      } else if (!hasOnlyLettersAndSpaces(data.nombre2)) {
        e.nombre2 = "Use solo letras y espacios";
      }
      if (!data.cargo2) {
        e.cargo2 = "Seleccione cargo";
      }
      if (!data.fecha2) {
        e.fecha2 = "Ingrese fecha";
      } else if (!isInstitutionalDate(data.fecha2)) {
        e.fecha2 = "La fecha debe ser igual o posterior al 01/01/2010";
      } else if (data.fecha2 > todayIso) {
        e.fecha2 = "La fecha no puede ser futura";
      }
    }

    if (
      mostrarAltaDirectivos &&
      faltaDirector &&
      faltaVicedirector &&
      data.cargo1 &&
      data.cargo2 &&
      data.cargo1 === data.cargo2
    ) {
      e.cargo2 = "No puede repetir el mismo cargo";
    }

    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitInFlight.current) return;
    if (!validate()) return;
    submitInFlight.current = true;
    hasStartedSave.current = true;
    setIsSubmitting(true);
    let directivoSlot: 1 | 2 | null = null;

    try {
      setSubmitError("");
      const uctPayload = {
        facultadRegional: data.facultadRegional.trim(),
        nombreSigla: data.nombreSigla.trim(),
        correo: data.correo.trim(),
        objetivos: data.objetivos.trim(),
      };
      const changedUctPayload = isEdit && uct
        ? Object.fromEntries(
            Object.entries(uctPayload).filter(
              ([key, value]) => value !== uct[key as keyof typeof uctPayload]
            )
          )
        : uctPayload;
      const hayCambiosUct = !isEdit || Object.keys(changedUctPayload).length > 0;
      const hayCambiosEquipo = Object.keys(pendingUpdates).length > 0 || Object.keys(pendingFinalizations).length > 0;
      if (hayCambiosUct) {
        await save(changedUctPayload);
      }

      for (const [id, nombre_apellido] of Object.entries(pendingUpdates)) {
        await actualizarDirectivo.mutateAsync({ id: Number(id), nombre_apellido });
      }
      for (const [id, fecha_fin] of Object.entries(pendingFinalizations)) {
        await finalizarDirectivo.mutateAsync({ id_directivo: Number(id), fecha_fin });
      }
      setPendingUpdates({});
      setPendingFinalizations({});

      if (grupoId && mostrarAltaDirectivos) {
        if (faltaDirector && !createdDirectivoSlots.current.has(1)) {
          directivoSlot = 1;
          await crearAsignar.mutateAsync({
            nombre_apellido: data.nombre1.trim(),
            id_cargo: Number(data.cargo1),
            fecha_inicio: data.fecha1,
          });
          createdDirectivoSlots.current.add(1);
        }

        if (faltaVicedirector && !createdDirectivoSlots.current.has(2)) {
          directivoSlot = 2;
          await crearAsignar.mutateAsync({
            nombre_apellido: data.nombre2.trim(),
            id_cargo: Number(data.cargo2),
            fecha_inicio: data.fecha2,
          });
          createdDirectivoSlots.current.add(2);
        }

        setMostrarAltaDirectivos(false);
        clearDraft();
        navigate("/inicio", {
          replace: true,
          state: { successMessage: "Equipo directivo registrado correctamente." },
        });
        return;
      }

      clearDraft();
      navigate("/inicio", {
        replace: true,
        state: {
          successMessage: isEdit
            ? hayCambiosEquipo
              ? hayCambiosUct
                ? "UCT y equipo directivo actualizados correctamente."
                : "Equipo directivo actualizado correctamente."
              : "UCT actualizada correctamente."
            : "UCT creada correctamente.",
        },
      });
    } catch (err: unknown) {
      if (directivoSlot) {
        const fields = getApiFieldErrors(err);
        const slot = directivoSlot;
        const controls: Record<string, string> = {
          nombre_apellido: `nombre${slot}`,
          id_cargo: `cargo${slot}`,
          fecha_inicio: `fecha${slot}`,
        };
        const mapped = Object.fromEntries(Object.entries(fields).flatMap(([key, value]) =>
          controls[key] ? [[controls[key], value]] : []
        ));
        if (Object.keys(mapped).length) {
          setErrors((previous) => ({ ...previous, ...mapped }));
          focusFieldErrors(mapped);
        }
        if (Object.keys(mapped).length && Object.keys(mapped).length === Object.keys(fields).length) return;
      }
      if (applyFieldErrors(err, setErrors, ["facultadRegional","nombreSigla","nombre1","cargo1","fecha1","nombre2","cargo2","fecha2","correo","objetivos"])) return;
      setSubmitError(
        getErrorMessage(
          err,
          "Lo sentimos, no pudimos guardar la UCT o su equipo directivo. Revise los datos e intente nuevamente."
        )
      );
    } finally {
      submitInFlight.current = false;
      setIsSubmitting(false);
    }
  };

  const handleEditarDirectivo = () => {
    if (!editingId || !editingNombre.trim()) return;
    if (!hasOnlyLettersAndSpaces(editingNombre)) {
      setSubmitError("Use solo letras y espacios en el nombre del directivo.");
      return;
    }
    const nombreOriginal = directivosActuales.find((directivo) => directivo.id_directivo === editingId)?.nombre_apellido;
    setPendingUpdates((current) => {
      const next = { ...current };
      if (editingNombre.trim() === nombreOriginal) {
        delete next[editingId];
      } else {
        next[editingId] = editingNombre.trim();
      }
      return next;
    });
    setSubmitError("");
    setEditingId(null);
    setEditingNombre("");
  };

  const abrirConfirmFinalizar = (directivo: DirectivoItem) => {
    setDirectivoAFinalizar(directivo);
    setFechaFin("");
    setConfirmOpen(true);
    setEditingId(null);
    setEditingNombre("");
  };

  const cerrarConfirmFinalizar = () => {
    setConfirmOpen(false);
    setFechaFin("");
    setDirectivoAFinalizar(null);
  };

  const handleFinalizarDirectivo = () => {
    const directivoId =
      directivoAFinalizar?.id_directivo ?? directivoAFinalizar?.id;

    if (!directivoId || !fechaFin) return;
    if (!isInstitutionalDate(fechaFin) || fechaFin > todayIso) return;
    if (
      directivoAFinalizar?.fecha_inicio &&
      fechaFin < directivoAFinalizar.fecha_inicio
    ) return;

    setPendingFinalizations((current) => ({ ...current, [directivoId]: fechaFin }));
    cerrarConfirmFinalizar();
  };

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-3xl font-semibold mb-6">Configuración de la UCT</h2>

      {availableDraft && (
        <DraftRecoveryNotice
          savedAt={availableDraft.saved_at}
          sourceChanged={sourceChanged}
          onRestore={restoreDraft}
          onDiscard={discardDraft}
        />
      )}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />

      <form
        noValidate
        onSubmit={onSubmit}
        className="rounded-2xl border border-slate-200 bg-white p-6 space-y-8"
      >
        {submitError && <ErrorText>{submitError}</ErrorText>}
        <Field required label="Facultad Regional" name="facultadRegional" error={errors.facultadRegional}>
          <>
            <input
              className={inputClass("facultadRegional")}
              value={data.facultadRegional}
              onChange={change("facultadRegional")}
            />
            {errors.facultadRegional && (
              <ErrorText>{errors.facultadRegional}</ErrorText>
            )}
          </>
        </Field>

        <Field required label="Nombre y Sigla del Grupo" name="nombreSigla" error={errors.nombreSigla}>
          <>
            <input
              className={inputClass("nombreSigla")}
              value={data.nombreSigla}
              onChange={change("nombreSigla")}
            />
            {errors.nombreSigla && <ErrorText>{errors.nombreSigla}</ErrorText>}
          </>
        </Field>

        {!isEdit && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
            Primero guardá la configuración del grupo. Después vas a poder
            registrar el equipo directivo.
          </div>
        )}

        {(faltaDirector || faltaVicedirector) && mostrarAltaDirectivos && (
          <div className="border border-slate-200 rounded-xl p-6 bg-slate-50 space-y-6">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-slate-700">
                Equipo Directivo
              </h3>
              <p className="text-sm text-slate-600">
                Completá los cargos directivos faltantes.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {faltaDirector && (
                <>
                  <Field required label="Nombre completo" name="nombre1" error={errors.nombre1}>
                    <>
                      <input
                        className={inputClass("nombre1")}
                        value={data.nombre1}
                        onChange={change("nombre1")}
                        placeholder="Ingrese nombre del director"
                      />
                      {errors.nombre1 && <ErrorText>{errors.nombre1}</ErrorText>}
                    </>
                  </Field>

                  <Field required label="Cargo" name="cargo1" error={errors.cargo1}>
                    <>
                      <select
                        className={inputClass("cargo1")}
                        value={data.cargo1}
                        onChange={change("cargo1")}
                      >
                        <option value="">Seleccione cargo</option>
                        {cargoDirector && (
                          <option value={cargoDirector.id}>
                            {cargoDirector.nombre}
                          </option>
                        )}
                      </select>
                      {errors.cargo1 && <ErrorText>{errors.cargo1}</ErrorText>}
                    </>
                  </Field>

                  <Field required label="Fecha de inicio" name="fecha1" error={errors.fecha1}>
                    <>
                      <input
                        type="date"
                        min={INSTITUTIONAL_MIN_DATE_ISO}
                        max={todayIso}
                        className={inputClass("fecha1")}
                        value={data.fecha1}
                        onChange={change("fecha1")}
                      />
                      {errors.fecha1 && <ErrorText>{errors.fecha1}</ErrorText>}
                    </>
                  </Field>
                </>
              )}

              {faltaVicedirector && (
                <>
                  <Field required label="Nombre completo" name="nombre2" error={errors.nombre2}>
                    <>
                      <input
                        className={inputClass("nombre2")}
                        value={data.nombre2}
                        onChange={change("nombre2")}
                        placeholder="Ingrese nombre del vicedirector"
                      />
                      {errors.nombre2 && <ErrorText>{errors.nombre2}</ErrorText>}
                    </>
                  </Field>

                  <Field required label="Cargo" name="cargo2" error={errors.cargo2}>
                    <>
                      <select
                        className={inputClass("cargo2")}
                        value={data.cargo2}
                        onChange={change("cargo2")}
                      >
                        <option value="">Seleccione cargo</option>
                        {cargoVicedirector && (
                          <option value={cargoVicedirector.id}>
                            {cargoVicedirector.nombre}
                          </option>
                        )}
                      </select>
                      {errors.cargo2 && <ErrorText>{errors.cargo2}</ErrorText>}
                    </>
                  </Field>

                  <Field required label="Fecha de inicio" name="fecha2" error={errors.fecha2}>
                    <>
                      <input
                        type="date"
                        min={INSTITUTIONAL_MIN_DATE_ISO}
                        max={todayIso}
                        className={inputClass("fecha2")}
                        value={data.fecha2}
                        onChange={change("fecha2")}
                      />
                      {errors.fecha2 && <ErrorText>{errors.fecha2}</ErrorText>}
                    </>
                  </Field>
                </>
              )}
            </div>

            <div className="flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setMostrarAltaDirectivos(false)}
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}

        {isEdit && tieneDirectivos && (
          <div className="border border-slate-200 rounded-xl p-6 bg-slate-50 space-y-4">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-slate-700">
                Equipo Directivo
              </h3>
              <p className="text-sm text-slate-600">
                El equipo directivo ya fue registrado para esta UCT.
              </p>

              {(faltaDirector || faltaVicedirector) && !mostrarAltaDirectivos && (
                <div className="pt-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setMostrarAltaDirectivos(true)}
                  >
                    Agregar cargo faltante
                  </Button>
                </div>
              )}
            </div>

            <div className="grid md:grid-cols-2 gap-4 text-sm text-slate-700">
              {directivosActuales.map((d, index) => {
                const directivoId = d.id_directivo;

                return (
                  <div
                    key={`${directivoId ?? index}-${d.cargo}`}
                    className="rounded-lg border border-slate-200 bg-white p-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium text-slate-900">
                          {directivoId && pendingUpdates[directivoId]
                            ? pendingUpdates[directivoId]
                            : d.nombre_apellido}
                        </p>
                        <p>{d.cargo}</p>
                        <p className="text-slate-500">
                          Inicio: {d.fecha_inicio || "—"}
                        </p>
                        {directivoId && pendingFinalizations[directivoId] && (
                          <p className="text-amber-700">
                            Finalización pendiente: {pendingFinalizations[directivoId]}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-3 pt-1">
                        <button
                          type="button"
                          onClick={() => {
                            if (!directivoId) return;
                            setEditingId(directivoId);
                            setEditingNombre(pendingUpdates[directivoId] ?? d.nombre_apellido);
                          }}
                          className="text-sky-600 hover:text-sky-700 transition"
                          title="Editar directivo"
                          aria-label={`Editar nombre de ${d.nombre_apellido}`}
                        >
                          <Pencil size={16} />
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            if (!directivoId) return;
                            abrirConfirmFinalizar(d);
                          }}
                          className="text-red-500 hover:text-red-600 transition"
                          title="Finalizar cargo"
                          aria-label={`Finalizar cargo de ${d.nombre_apellido}`}
                        >
                          <X size={16} aria-hidden="true" />
                        </button>
                      </div>
                    </div>

                    {editingId === directivoId && (
                      <div className="mt-4 border-t border-slate-200 pt-4 space-y-3">
                        <input
                          className="input"
                          value={editingNombre}
                          onChange={(e) => setEditingNombre(e.target.value)}
                          placeholder="Nombre y apellido"
                        />

                        <div className="flex justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setEditingId(null);
                              setEditingNombre("");
                            }}
                          >
                            Cancelar
                          </Button>

                          <Button
                            type="button"
                            size="sm"
                            onClick={handleEditarDirectivo}
                            disabled={isSubmitting}
                         >
                            Aplicar al formulario
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {(Object.keys(pendingUpdates).length > 0 ||
          Object.keys(pendingFinalizations).length > 0) && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3" role="status">
            <p className="text-sm text-amber-900">
              Hay cambios del equipo directivo pendientes. Para actualizar el nombre y registrar el cambio en el historial, guarde la UCT.
            </p>
            <Button type="submit" size="sm" disabled={isSubmitting} loading={isSubmitting} loadingText="Guardando...">
              Guardar cambios de la UCT
            </Button>
          </div>
        )}

        {isEdit && isLoadingDirectivos && (
          <LoadingSkeleton variant="compact" label="Cargando equipo directivo…" />
        )}

        {isEdit && !isLoadingDirectivos && !tieneDirectivos && !mostrarAltaDirectivos && (
          <div className="border border-slate-200 rounded-xl p-6 bg-slate-50 space-y-4">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-slate-700">
                Equipo Directivo
              </h3>
              <p className="text-sm text-slate-600">
                Todavía no hay cargos directivos registrados para esta UCT.
              </p>
            </div>

            <div className="pt-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setMostrarAltaDirectivos(true)}
              >
                Registrar equipo directivo
              </Button>
            </div>
          </div>
        )}

        <Field required label="Correo electrónico" name="correo" error={errors.correo}>
          <>
            <input
              type="email"
              className={inputClass("correo")}
              value={data.correo}
              onChange={change("correo")}
            />
            {errors.correo && <ErrorText>{errors.correo}</ErrorText>}
          </>
        </Field>

        <Field required label="Objetivos" name="objetivos" error={errors.objetivos}>
          <>
            <textarea
              rows={5}
              className={`${inputClass("objetivos")} resize-y`}
              value={data.objetivos}
              onChange={change("objetivos")}
            />
            {errors.objetivos && <ErrorText>{errors.objetivos}</ErrorText>}
          </>
        </Field>

        <div className="flex justify-between pt-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => requestLeave(() => navigate(-1))}
            disabled={isSubmitting}
          >
            Volver
          </Button>

          <Button
            type="submit"
            disabled={isSubmitting}
            size="sm"
           loading={isSubmitting}
           loadingText="Guardando..."
         >
            {isSubmitting
              ? "Guardando…"
              : !isEdit
                ? "Guardar grupo"
                : mostrarAltaDirectivos && (faltaDirector || faltaVicedirector)
                  ? "Guardar y registrar directivos"
                  : "Guardar cambios"}
          </Button>
        </div>
      </form>

      <ConfirmDialog
        open={confirmOpen}
        title="Finalizar cargo directivo"
        message="¿Estás seguro de finalizar este cargo? Esta acción removerá al directivo del equipo actual."
        items={
          directivoAFinalizar
            ? [`${directivoAFinalizar.nombre_apellido} — ${directivoAFinalizar.cargo}`]
            : []
        }
        confirmText={
          finalizarDirectivo.isPending ? "Finalizando..." : "Aceptar"
        }
        confirmDisabled={
          !fechaFin ||
          !isInstitutionalDate(fechaFin) ||
          fechaFin > todayIso ||
          Boolean(
            directivoAFinalizar?.fecha_inicio &&
            fechaFin < directivoAFinalizar.fecha_inicio
          ) ||
          finalizarDirectivo.isPending
        }
        onCancel={cerrarConfirmFinalizar}
        onConfirm={handleFinalizarDirectivo}
       loadingText="Procesando..."
     >
        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-700">
            Fecha de finalización<span className="ml-1 text-rose-500" aria-hidden="true">*</span>
          </label>
          <input
            type="date"
            min={directivoAFinalizar?.fecha_inicio ?? INSTITUTIONAL_MIN_DATE_ISO}
            max={todayIso}
            className="input"
            value={fechaFin}
            onChange={(e) => setFechaFin(e.target.value)}
          />
          {!fechaFin && (
            <p className="text-sm text-red-600">
              Debe ingresar una fecha de finalización.
            </p>
          )}
          {fechaFin && !isInstitutionalDate(fechaFin) && (
            <p className="text-sm text-red-600">
              La fecha debe ser igual o posterior al 01/01/2010.
            </p>
          )}
          {fechaFin && fechaFin > todayIso && (
            <p className="text-sm text-red-600">
              La fecha no puede ser futura.
            </p>
          )}
          {fechaFin && directivoAFinalizar?.fecha_inicio &&
            fechaFin < directivoAFinalizar.fecha_inicio && (
              <p className="text-sm text-red-600">
                La fecha de finalización no puede ser anterior al inicio.
              </p>
            )}
        </div>
      </ConfirmDialog>

    </section>
  );
}
