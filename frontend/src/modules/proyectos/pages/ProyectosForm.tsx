import LoadingSkeleton from "@/components/LoadingSkeleton";
import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { hasLetter } from "../../../lib/textValidation";
import { LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Button from "@/components/Button";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import Calendar from "@/components/Calendar";
import Field from "@/components/Field";
import PersonalProyectoField from "@/modules/proyectos/components/PersonalProyectoField";
import SuccessToast from "@/components/SuccessToast";
import { useBecarios } from "@/modules/personal/hooks/useBecarios";
import { useFuentesFinanciamiento } from "@/modules/catalogos/hooks/useFuenteFinanciamiento";
import { getInvestigadores } from "@/modules/personal/services/investigadorServices";
import { useTiposProyecto } from "@/modules/proyectos/hooks/useTiposProyecto";
import { useUct } from "@/modules/grupo/hooks/useUct";
import { getErrorMessage } from "@/lib/httpError";
import {
  getProyectoById,
  type Proyecto,
  type ProyectoPayload,
  upsertProyectos,
} from "@/modules/proyectos/services/proyectosServices";
import {
  PROYECTO_CODIGO_MAX_LENGTH,
  validateCodigoProyecto,
  validateDuracionProyecto,
} from "@/modules/proyectos/utils/proyectoValidation";
import { parseCivilDate, toCivilDateString } from "@/utils/dateTime";
import { useAuth } from "@/context/AuthContext";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";

type ProyectoDraft = {
  nombreProyecto: string;
  codigoProyecto: string;
  descripcionProyecto: string;
  logrosObtenidos: string;
  dificultadesProyecto: string;
  montoDestinado: string;
  fechaInicio: string | null;
  fechaFin: string | null;
  tipoProyectoId: number | null;
  fuenteId: number | null;
  investigadoresIds: number[];
  coordinadorId: number | null;
  becariosIds: number[];
};

export default function ProyectosForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const isEdit = Boolean(id);

  const tiposQuery = useTiposProyecto();
  const fuentesQuery = useFuentesFinanciamiento();
  const investigadoresQuery = useQuery({
    queryKey: ["proyecto-candidatos"], queryFn: getInvestigadores, refetchOnMount: "always",
  });
  const investigadores = investigadoresQuery.data ?? [];
  const { data: becarios = [] } = useBecarios();
  const { uct } = useUct();

  const tipos = tiposQuery.data || [];
  const { fuentes = [] } = fuentesQuery;

  const { data: initialData, isLoading } = useQuery<Proyecto | null>({
    queryKey: ["proyecto", id],
    queryFn: () =>
      id ? getProyectoById(Number(id)) : Promise.resolve(null),
    enabled: isEdit,
  });

  const [nombreProyecto, setNombreProyecto] = useState("");
  const [codigoProyecto, setCodigoProyecto] = useState("");
  const [descripcionProyecto, setDescripcionProyecto] = useState("");
  const [logrosObtenidos, setLogrosObtenidos] = useState("");
  const [dificultadesProyecto, setDificultadesProyecto] = useState("");
  const [montoDestinado, setMontoDestinado] = useState("");

  const [fechaInicio, setFechaInicio] = useState<Date | null>(null);
  const [fechaFin, setFechaFin] = useState<Date | null>(null);
  const [tipoProyectoId, setTipoProyectoId] = useState<number | null>(null);
  const [fuenteId, setFuenteId] = useState<number | null>(null);

  const [investigadoresIds, setInvestigadoresIds] = useState<number[]>([]);
  const [coordinadorId, setCoordinadorId] = useState<number | null>(null);
  const [becariosIds, setBecariosIds] = useState<number[]>([]);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [formInitialized, setFormInitialized] = useState(!isEdit);
  const [coordinatorPage, setCoordinatorPage] = useState(1);

  const proyectoCerrado = initialData?.cerrado === true || initialData?.activo === false || !!initialData?.deleted_at;

  useEffect(() => {
    if (!initialData) return;

    setNombreProyecto(initialData.nombreProyecto ?? "");
    setCodigoProyecto(initialData.codigoProyecto ?? "");
    setDescripcionProyecto(initialData.descripcionProyecto ?? "");
    setLogrosObtenidos(initialData.logrosObtenidos ?? "");
    setDificultadesProyecto(initialData.dificultadesProyecto ?? "");
    setMontoDestinado(
      initialData.montoDestinado !== undefined &&
        initialData.montoDestinado !== null
        ? String(initialData.montoDestinado)
        : ""
    );

    setFechaInicio(
      parseCivilDate(initialData.fechaInicio)
    );
    setFechaFin(
      parseCivilDate(initialData.fechaFinalizacion)
    );

    setTipoProyectoId(initialData.tipoProyectoId ?? null);
    setFuenteId(initialData.fuenteFinanciamientoId ?? null);

    const investigadoresIniciales =
      initialData.investigadores?.map((investigador) => investigador.id) ?? [];
    setInvestigadoresIds(investigadoresIniciales);

    const coordinadorInicial =
      initialData.investigadores?.find(
        (investigador) => investigador.es_coordinador
      )?.id ?? null;
    setCoordinadorId(coordinadorInicial);

    setBecariosIds(initialData.becarios?.map((becario) => becario.id) ?? []);
    setFormInitialized(true);
  }, [initialData]);

  useEffect(() => {
    if (coordinadorId !== null && !investigadoresIds.includes(coordinadorId)) {
      setCoordinadorId(null);
    }
  }, [coordinadorId, investigadoresIds]);

  const draftValue = useMemo<ProyectoDraft>(() => ({
    nombreProyecto,
    codigoProyecto,
    descripcionProyecto,
    logrosObtenidos,
    dificultadesProyecto,
    montoDestinado,
    fechaInicio: toCivilDateString(fechaInicio),
    fechaFin: toCivilDateString(fechaFin),
    tipoProyectoId,
    fuenteId,
    investigadoresIds,
    coordinadorId,
    becariosIds,
  }), [
    becariosIds, codigoProyecto, coordinadorId, descripcionProyecto,
    logrosObtenidos,
    dificultadesProyecto, fechaFin, fechaInicio, fuenteId, investigadoresIds,
    montoDestinado, nombreProyecto, tipoProyectoId,
  ]);

  const { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave } = useFormDraft({
    userId: user?.id,
    module: "proyectos",
    recordId: id,
    value: draftValue,
    ready: formInitialized,
    autosave: false,
    hasContent: (draft) => Boolean(
      draft.nombreProyecto || draft.codigoProyecto || draft.descripcionProyecto ||
      draft.logrosObtenidos || draft.dificultadesProyecto || draft.montoDestinado || draft.fechaInicio ||
      draft.fechaFin || draft.tipoProyectoId || draft.fuenteId ||
      draft.investigadoresIds.length || draft.becariosIds.length
    ),
    onRestore: (draft) => {
      setNombreProyecto(draft.nombreProyecto);
      setCodigoProyecto(draft.codigoProyecto);
      setDescripcionProyecto(draft.descripcionProyecto);
      setLogrosObtenidos(draft.logrosObtenidos ?? "");
      setDificultadesProyecto(draft.dificultadesProyecto);
      setMontoDestinado(draft.montoDestinado);
      setFechaInicio(parseCivilDate(draft.fechaInicio));
      setFechaFin(parseCivilDate(draft.fechaFin));
      setTipoProyectoId(draft.tipoProyectoId);
      setFuenteId(draft.fuenteId);
      setInvestigadoresIds(draft.investigadoresIds);
      setCoordinadorId(draft.coordinadorId);
      setBecariosIds(draft.becariosIds);
    },
  });

  const investigadoresSeleccionados = useMemo(() => {
    const disponibles = [...investigadores, ...(initialData?.investigadores ?? [])
      .filter(i => !investigadores.some(c => c.id === i.id))];
    return disponibles.filter((investigador) =>
      investigadoresIds.includes(investigador.id)
    );
  }, [investigadores, investigadoresIds, initialData]);
  const currentCoordinatorPage = Math.min(coordinatorPage, Math.max(1, Math.ceil(investigadoresSeleccionados.length / 5)));

  const investigadoresInicialesIds = useMemo(
    () => initialData?.investigadores?.map((investigador) => investigador.id) ?? [],
    [initialData]
  );

  const becariosInicialesIds = useMemo(
    () => initialData?.becarios?.map((becario) => becario.id) ?? [],
    [initialData]
  );

  const coordinadorInicialId = useMemo(
    () =>
      initialData?.investigadores?.find(
        (investigador) => investigador.es_coordinador
      )?.id ?? null,
    [initialData]
  );

  const mutation = useMutation({
    mutationFn: (payload: ProyectoPayload) => upsertProyectos(payload),
    onSuccess: () => {
      clearDraft();
      qc.invalidateQueries({ queryKey: ["proyectos"] });
      qc.invalidateQueries({ queryKey: ["proyecto", id] });
      qc.invalidateQueries({ queryKey: ["proyecto-historial", id] });

      if (isEdit && id) {
        navigate(`/proyectos/${id}`, {
          replace: true,
          state: {
            successMessage: "Proyecto actualizado con éxito.",
          },
        });
        return;
      }

      navigate("/proyectos", {
        state: {
          successMessage: "Proyecto creado con éxito.",
        },
      });
    },
    onError: (error) => {
      if (applyFieldErrors(error, setErrors, ["codigoProyecto","nombreProyecto","tipoProyectoId","fechaInicio","montoDestinado","coordinadorId","investigadoresIds","descripcionProyecto","dificultadesProyecto","logrosObtenidos","fuenteId","becariosIds","fechaFin"])) return;
      const defaultMessage = isEdit
        ? "Lo sentimos, no pudimos actualizar el proyecto. Revise los datos e intente nuevamente."
        : "Lo sentimos, no pudimos crear el proyecto. Revise los datos e intente nuevamente.";

      setErrorMessage(getErrorMessage(error, defaultMessage));

      setShowError(true);
    },
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

    const codigoProyectoError = validateCodigoProyecto(codigoProyecto);
    if (codigoProyectoError) {
      newErrors.codigoProyecto = codigoProyectoError;
    }

    if (logrosObtenidos.length > 20000) {
      newErrors.logrosObtenidos = "Ingrese un texto de hasta 20000 caracteres.";
    }

    if (!nombreProyecto.trim()) {
      newErrors.nombreProyecto = "Debe ingresar nombre del proyecto";
    } else if (!hasLetter(nombreProyecto)) {
      newErrors.nombreProyecto = "El nombre del proyecto debe contener letras";
    }

    if (!tipoProyectoId) {
      newErrors.tipoProyectoId = "Debe seleccionar tipo de proyecto";
    }

    if (!fechaInicio) {
      newErrors.fechaInicio = "Debe seleccionar fecha de inicio";
    }
    if (!isEdit || toCivilDateString(fechaInicio) !== initialData?.fechaInicio || toCivilDateString(fechaFin) !== (initialData?.fechaFinalizacion ?? null)) {
      const durationError = validateDuracionProyecto(fechaInicio, fechaFin);
      if (durationError) newErrors.fechaFin = durationError;
    }

    if (
      montoDestinado.trim() !== "" &&
      (!Number.isFinite(Number(montoDestinado)) || Number(montoDestinado) < 0)
    ) {
      newErrors.montoDestinado = "El monto debe ser un numero mayor o igual a cero";
    }

    if (investigadoresIds.some(id => !Number.isInteger(id) || id <= 0)) {
      newErrors.investigadoresIds = "Complete o quite las selecciones vacías.";
    }
    if (becariosIds.some(id => !Number.isInteger(id) || id <= 0)) {
      newErrors.becariosIds = "Complete o quite las selecciones vacías.";
    }
    if (investigadoresQuery.isLoading || investigadoresQuery.isError) {
      newErrors.investigadoresIds = "Espere la carga de investigadores o intente nuevamente.";
    }
    if (investigadoresIds.length > 0 && coordinadorId === null) {
      newErrors.coordinadorId =
        "Debe seleccionar un coordinador entre los investigadores elegidos";
    }

    if (
      coordinadorId !== null &&
      !investigadoresIds.includes(coordinadorId)
    ) {
      newErrors.coordinadorId =
        "El coordinador debe ser uno de los investigadores seleccionados";
    }

    setErrors(newErrors);
    if (Object.keys(newErrors).length) {
      focusFieldErrors(newErrors);
      setErrorMessage("No pudimos guardar el proyecto. Complete o corrija los campos indicados e intente nuevamente.");
      setShowError(true);
    }
    return Object.keys(newErrors).length === 0;
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mutation.isPending) return;

    if (proyectoCerrado) return;
    if (!validate()) return;

    const payload = {
      id: id ?? undefined,
      nombreProyecto,
      codigoProyecto: codigoProyecto.trim(),
      descripcionProyecto,
      logrosObtenidos,
      dificultadesProyecto,
      montoDestinado:
        montoDestinado.trim() !== ""
          ? Number(montoDestinado)
          : undefined,
      grupoUtnId: uct?.id ?? undefined,
      fechaInicio: toCivilDateString(fechaInicio) ?? undefined,
      fechaFinalizacion: fechaFin
        ? toCivilDateString(fechaFin)
        : undefined,
      tipoProyectoId,
      fuenteFinanciamientoId: fuenteId ?? undefined,
    };

    if (!isEdit) {
      mutation.mutate({ ...payload, investigadoresIds, becariosIds, coordinadorId });
      return;
    }

    const initialPayload = {
      nombreProyecto: initialData?.nombreProyecto ?? "",
      codigoProyecto: initialData?.codigoProyecto ?? "",
      descripcionProyecto: initialData?.descripcionProyecto ?? "",
      logrosObtenidos: initialData?.logrosObtenidos ?? "",
      dificultadesProyecto: initialData?.dificultadesProyecto ?? "",
      montoDestinado:
        initialData?.montoDestinado !== undefined &&
        initialData?.montoDestinado !== null
          ? Number(initialData.montoDestinado)
          : undefined,
      grupoUtnId: initialData?.grupoUtnId ?? uct?.id ?? undefined,
      fechaInicio: initialData?.fechaInicio ?? undefined,
      fechaFinalizacion: initialData?.fechaFinalizacion ?? undefined,
      tipoProyectoId: initialData?.tipoProyectoId ?? null,
      fuenteFinanciamientoId: initialData?.fuenteFinanciamientoId ?? undefined,
    };

    const changedPayload = Object.fromEntries(
      Object.entries(payload).filter(([key, value]) => {
        if (key === "id") return false;
        return initialPayload[key as keyof typeof initialPayload] !== value;
      })
    );

    const hayNuevosInvestigadores = investigadoresIds.some(
      (idInvestigador) => !investigadoresInicialesIds.includes(idInvestigador)
    );
    const hayNuevosBecarios = becariosIds.some(
      (idBecario) => !becariosInicialesIds.includes(idBecario)
    );
    const hayInvestigadoresDesvinculados = investigadoresInicialesIds.some(
      (idInvestigador) => !investigadoresIds.includes(idInvestigador)
    );
    const hayBecariosDesvinculados = becariosInicialesIds.some(
      (idBecario) => !becariosIds.includes(idBecario)
    );
    const cambioCoordinador = coordinadorInicialId !== coordinadorId;

    if (
      Object.keys(changedPayload).length === 0 &&
      !hayNuevosInvestigadores &&
      !hayNuevosBecarios &&
      !hayInvestigadoresDesvinculados &&
      !hayBecariosDesvinculados &&
      !cambioCoordinador
    ) {
      clearDraft();
      navigate(`/proyectos/${id}`, {
        replace: true,
        state: {
          successMessage: "No hubo cambios para actualizar.",
        },
      });
      return;
    }

    mutation.mutate(
      {
        ...changedPayload, id,
        ...(hayNuevosInvestigadores || hayInvestigadoresDesvinculados ? { investigadoresIds } : {}),
        ...(hayNuevosBecarios || hayBecariosDesvinculados ? { becariosIds } : {}),
        ...(cambioCoordinador ? { coordinadorId } : {}),
      }
    );
  };

  if (isEdit && isLoading) {
    return <LoadingSkeleton variant="form" label="Cargando proyecto..." />;
  }

  const inputClass = (field: string) =>
    `input ${errors[field] ? "!border-red-500 !ring-2 !ring-red-500" : ""}`;

  return (
    <section className="w-full">
      <h2 className="text-2xl md:text-3xl font-semibold leading-none">
        {isEdit ? "Editar proyecto" : "Nuevo proyecto"}
      </h2>

      {proyectoCerrado && (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Este proyecto se encuentra {initialData?.cerrado ? "cerrado" : "inactivo"}. Para modificar investigadores,
          becarios o volver a editarlo, primero debes reabrirlo desde el
          detalle.
        </div>
      )}

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
        onSubmit={submit}
        className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6"
      >
        <Field required label="Código del proyecto" name="codigoProyecto" error={errors.codigoProyecto}>
          <>
            <input
              id="codigo-proyecto"
              className={inputClass("codigoProyecto")}
              value={codigoProyecto}
              onChange={(e) => {
                setCodigoProyecto(e.target.value);
                clearError("codigoProyecto");
              }}
              placeholder="Ej: LPSIEC1347"
              maxLength={PROYECTO_CODIGO_MAX_LENGTH}
              aria-label="Código del proyecto"
              aria-invalid={Boolean(errors.codigoProyecto)}
              aria-describedby={
                errors.codigoProyecto ? "codigo-proyecto-error" : undefined
              }
              disabled={proyectoCerrado}
            />
            {errors.codigoProyecto && (
              <p
                id="codigo-proyecto-error"
                role="alert"
                className="mt-1 text-sm text-red-500"
              >
                {errors.codigoProyecto}
              </p>
            )}
          </>
        </Field>

        <Field required label="Nombre del proyecto" name="nombreProyecto" error={errors.nombreProyecto}>
          <>
            <input
              className={inputClass("nombreProyecto")}
              value={nombreProyecto}
              onChange={(e) => {
                setNombreProyecto(e.target.value);
                if (e.target.value.trim()) clearError("nombreProyecto");
              }}
              placeholder="Ingrese el nombre del proyecto"
              disabled={proyectoCerrado}
            />
            {errors.nombreProyecto && (
              <p className="mt-1 text-sm text-red-500">
                {errors.nombreProyecto}
              </p>
            )}
          </>
        </Field>

        <Field label="Descripción del proyecto" name="descripcionProyecto" error={errors.descripcionProyecto}>
          <textarea
            className="input min-h-[100px]"
            value={descripcionProyecto}
            onChange={(e) => setDescripcionProyecto(e.target.value)}
            placeholder="Describe detalladamente los objetivos, metodología y alcance del proyecto."
            required
            disabled={proyectoCerrado}
          />
        </Field>

        <Field label="Logros obtenidos" name="logrosObtenidos" error={errors.logrosObtenidos}>
          <textarea
            className="input min-h-[100px]"
            value={logrosObtenidos}
            onChange={(e) => setLogrosObtenidos(e.target.value)}
            maxLength={20000}
            placeholder="Describa los resultados y avances obtenidos por el proyecto."
            disabled={proyectoCerrado}
          />
          <p className="mt-1 text-xs text-slate-500">Este contenido se incorpora a la memoria al cerrar su versión.</p>
        </Field>

        <Field label="Dificultades del proyecto" name="dificultadesProyecto" error={errors.dificultadesProyecto}>
          <textarea
            className="input min-h-[100px]"
            value={dificultadesProyecto}
            onChange={(e) => setDificultadesProyecto(e.target.value)}
            placeholder="Describe dificultades, riesgos o bloqueos del proyecto."
            disabled={proyectoCerrado}
          />
        </Field>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Field required label="Tipo de proyecto" name="tipoProyectoId" error={errors.tipoProyectoId}>
            <>
              <select
                className={inputClass("tipoProyectoId")}
                value={tipoProyectoId ?? ""}
                onChange={(e) => {
                  const value = e.target.value ? Number(e.target.value) : null;
                  setTipoProyectoId(value);
                  if (value) clearError("tipoProyectoId");
                }}
                disabled={proyectoCerrado}
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
              {errors.tipoProyectoId && (
                <p className="mt-1 text-sm text-red-500">
                  {errors.tipoProyectoId}
                </p>
              )}
            </>
          </Field>

          <Field label="Fuente de financiamiento" name="fuenteId" error={errors.fuenteId}>
            <select
              className="input"
              value={fuenteId ?? ""}
              onChange={(e) =>
                setFuenteId(e.target.value ? Number(e.target.value) : null)
              }
              disabled={proyectoCerrado}
            >
              <option value="">Sin fuente</option>
              {fuentes.map((fuente) => (
                <option key={fuente.id} value={fuente.id}>
                  {fuente.nombre}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Field label="Monto destinado" name="montoDestinado" error={errors.montoDestinado}>
            <>
              <input
                type="number"
                min="0"
                step="0.01"
                className={inputClass("montoDestinado")}
                value={montoDestinado}
                onChange={(e) => {
                  setMontoDestinado(e.target.value);
                  clearError("montoDestinado");
                }}
                placeholder="Ej: 1500000"
                disabled={proyectoCerrado}
              />
              {errors.montoDestinado && (
                <p className="mt-1 text-sm text-red-500">
                  {errors.montoDestinado}
                </p>
              )}
            </>
          </Field>
        </div>

        <Field label="Investigadores" name="investigadoresIds" error={errors.investigadoresIds}>
          <div className="space-y-4" data-error-field="coordinadorId" tabIndex={-1}>
            {investigadoresQuery.isLoading && <LoadingSkeleton variant="compact" label="Cargando investigadores..." />}
            {investigadoresQuery.isError && <div role="alert">
              <p>Lo sentimos, no pudimos recuperar los investigadores. Intente nuevamente.</p>
              <Button type="button" variant="secondary" onClick={() => void investigadoresQuery.refetch()} loading={investigadoresQuery.isFetching} loadingText="Reintentando...">Reintentar</Button>
            </div>}
            {!investigadoresQuery.isLoading && !investigadoresQuery.isError && investigadores.length === 0 &&
              <p role="status">No hay investigadores activos disponibles. Registre o reactive un investigador para asignar un coordinador.</p>}
            {investigadoresSeleccionados.length === 0 && investigadores.length > 0 &&
              <p>Agregue un investigador al proyecto para seleccionar su coordinador.</p>}
            <PersonalProyectoField
              label="investigadores"
              value={investigadoresIds}
              options={[
                ...investigadores,
                ...(initialData?.investigadores ?? []).filter(i => !investigadores.some(c => c.id === i.id)),
              ]}
              disabled={proyectoCerrado || investigadoresQuery.isLoading || investigadoresQuery.isError}
              onChange={(ids) => {
                if (proyectoCerrado) return;
                setInvestigadoresIds(ids);
                clearError("investigadoresIds");
                clearError("coordinadorId");
              }}
            />

            {investigadoresSeleccionados.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="mb-3 text-sm font-medium text-slate-800">
                  Seleccionar coordinador<span className="ml-1 text-rose-500" aria-hidden="true">*</span>
                </p>

                <div className="space-y-2">
                  {investigadoresSeleccionados.slice((currentCoordinatorPage - 1) * 5, currentCoordinatorPage * 5).map((investigador) => (
                    <label
                      key={investigador.id}
                      className={`flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 ${
                        proyectoCerrado
                          ? "cursor-not-allowed opacity-60"
                          : "cursor-pointer"
                      }`}
                    >
                      <input
                        type="radio"
                        name="coordinador"
                        checked={coordinadorId === investigador.id}
                        onChange={() => {
                          if (proyectoCerrado) return;
                          setCoordinadorId(investigador.id);
                          clearError("coordinadorId");
                        }}
                        disabled={proyectoCerrado || (!investigadores.some(c => c.id === investigador.id) && coordinadorId !== investigador.id)}
                      />
                      <span className="text-sm text-slate-700">
                        {investigador.nombre_apellido}{!investigadores.some(c => c.id === investigador.id) ? " (inactivo, asignación conservada)" : ""}
                      </span>
                    </label>
                  ))}
                </div>

                {investigadoresSeleccionados.length > 5 && <nav aria-label="Páginas de candidatos a coordinador" className="mt-3 flex items-center gap-2 text-sm">
                  <Button type="button" variant="secondary" size="sm" disabled={currentCoordinatorPage === 1} onClick={() => setCoordinatorPage(currentCoordinatorPage - 1)}>Anterior</Button>
                  <span role="status">Página {currentCoordinatorPage} de {Math.ceil(investigadoresSeleccionados.length / 5)}</span>
                  <Button type="button" variant="secondary" size="sm" disabled={currentCoordinatorPage === Math.ceil(investigadoresSeleccionados.length / 5)} onClick={() => setCoordinatorPage(currentCoordinatorPage + 1)}>Siguiente</Button>
                </nav>}

                <p className="mt-3 text-xs text-slate-500">
                  Solo un investigador puede quedar marcado como coordinador.
                </p>
              </div>
            )}

            {errors.coordinadorId && (
              <p className="mt-1 text-sm text-red-500">
                {errors.coordinadorId}
              </p>
            )}
          </div>
        </Field>

        <Field label="Becarios" name="becariosIds" error={errors.becariosIds}>
          <PersonalProyectoField
            label="becarios"
            value={becariosIds}
            options={[
              ...becarios,
              ...(initialData?.becarios ?? []).filter((becario) => !becarios.some((candidate) => candidate.id === becario.id)),
            ]}
            onChange={(ids) => {
              if (proyectoCerrado) return;
              setBecariosIds(ids);
            }}
          />
        </Field>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Field required label="Fecha inicio" name="fechaInicio" error={errors.fechaInicio}>
            <Calendar
              value={fechaInicio}
              onChange={(date) => {
                if (proyectoCerrado || initialData?.fechaFinProrrogada) return;
                setFechaInicio(date);
                if (date) clearError("fechaInicio");
              }}
              className={inputClass("fechaInicio")}
              helperText="DD/MM/AAAA"
            />
          </Field>

          <Field required label={initialData?.fechaFinProrrogada ? "Fecha fin vigente" : "Fecha fin inicial"} name="fechaFin" error={errors.fechaFin}>
            <Calendar
              value={fechaFin}
              onChange={(date) => {
                if (proyectoCerrado || initialData?.fechaFinProrrogada) return;
                setFechaFin(date);
                if (date) clearError("fechaFin");
              }}
              minDate={fechaInicio ?? undefined}
              className="input"
            />
          </Field>
          {initialData?.fechaFinProrrogada && <p className="text-sm text-slate-500">Las fechas de un proyecto prorrogado no se pueden editar.</p>}
        </div>

        <div className="flex justify-between pt-6">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => requestLeave(() => navigate(-1))}
          >
            Volver
          </Button>

          {!proyectoCerrado && (
            <Button type="submit" size="sm" disabled={mutation.isPending} aria-busy={mutation.isPending} loading={mutation.isPending} loadingText="Guardando...">
              {mutation.isPending && <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />}
              {mutation.isPending
                ? "Guardando..."
                : isEdit
                  ? "Actualizar"
                  : "Guardar"}
            </Button>
          )}
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
