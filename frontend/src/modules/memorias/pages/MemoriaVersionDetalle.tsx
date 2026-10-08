import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/Button";
import SuccessToast from "@/components/SuccessToast";
import { useAuth } from "@/context/AuthContext";

import {
  exportarExcelMemoria,
  getActividadesDocenciaSnapshot,
  getArticulosDivulgacionSnapshot,
  getBecariosSnapshot,
  getDistincionesSnapshot,
  getDocumentacionBibliograficaSnapshot,
  getEquipamientoSnapshot,
  getErogacionesSnapshot,
  getInvestigadoresSnapshot,
  getMemoriaById,
  getParticipacionesRelevantesSnapshot,
  getPersonalSnapshot,
  getProyectosSnapshot,
  getRegistrosPropiedadSnapshot,
  getTrabajosReunionCientificaSnapshot,
  getTrabajosRevistasSnapshot,
  getTransferenciasSnapshot,
  getVisitasAcademicasSnapshot,
  type Memoria,
  type MemoriaSnapshotEntry,
} from "@/modules/memorias/services/memoriasService";
import {
  createPlanificacion,
  getPlanificaciones,
  updatePlanificacion,
  type PlanificacionGrupo,
} from "@/modules/grupo/services/planificacionGrupoServices";
import { formatFecha, getCivilYear } from "@/utils/dateTime";

type SnapshotSection = {
  key: string;
  label: string;
  queryKey: string;
  queryFn: (
    memoriaId: number,
    versionId: number
  ) => Promise<MemoriaSnapshotEntry[]>;
  homePath?: string;
};

const sections: SnapshotSection[] = [
  {
    key: "investigadores",
    label: "Investigadores",
    queryKey: "memoria-snapshot-investigadores",
    queryFn: getInvestigadoresSnapshot,
    homePath: "/personal?tipo=INVESTIGADOR",
  },
  {
    key: "becarios",
    label: "Becarios",
    queryKey: "memoria-snapshot-becarios",
    queryFn: getBecariosSnapshot,
    homePath: "/personal?tipo=BECARIO",
  },
  {
    key: "personal",
    label: "Personal",
    queryKey: "memoria-snapshot-personal",
    queryFn: getPersonalSnapshot,
    homePath: "/personal?tipo=PERSONAL",
  },
  {
    key: "proyectos",
    label: "Proyectos",
    queryKey: "memoria-snapshot-proyectos",
    queryFn: getProyectosSnapshot,
    homePath: "/proyectos",
  },
  {
    key: "actividades-docencia",
    label: "Actividades en docencia",
    queryKey: "memoria-snapshot-docencia",
    queryFn: getActividadesDocenciaSnapshot,
    homePath: "/docenciaInvestigador",
  },
  {
    key: "participaciones-relevantes",
    label: "Participaciones relevantes",
    queryKey: "memoria-snapshot-participaciones",
    queryFn: getParticipacionesRelevantesSnapshot,
    homePath: "/participaciones",
  },
  {
    key: "documentacion-bibliografica",
    label: "Documentación bibliográfica",
    queryKey: "memoria-snapshot-documentacion",
    queryFn: getDocumentacionBibliograficaSnapshot,
    homePath: "/documentacion",
  },
  {
    key: "equipamiento",
    label: "Equipamiento",
    queryKey: "memoria-snapshot-equipamiento",
    queryFn: getEquipamientoSnapshot,
    homePath: "/equipamiento",
  },
  {
    key: "erogaciones",
    label: "Erogaciones",
    queryKey: "memoria-snapshot-erogaciones",
    queryFn: getErogacionesSnapshot,
    homePath: "/movimientos",
  },
  {
    key: "transferencias",
    label: "Transferencias",
    queryKey: "memoria-snapshot-transferencias",
    queryFn: getTransferenciasSnapshot,
    homePath: "/transferencias",
  },
  {
    key: "trabajos-reunion-cientifica",
    label: "Trabajos en reunión científica",
    queryKey: "memoria-snapshot-reunion",
    queryFn: getTrabajosReunionCientificaSnapshot,
    homePath: "/trabajos-reunion",
  },
  {
    key: "trabajos-revistas",
    label: "Trabajos en revistas",
    queryKey: "memoria-snapshot-revistas",
    queryFn: getTrabajosRevistasSnapshot,
    homePath: "/trabajos-revistas",
  },
  {
    key: "distinciones",
    label: "Distinciones",
    queryKey: "memoria-snapshot-distinciones",
    queryFn: getDistincionesSnapshot,
    homePath: "/distinciones",
  },
  {
    key: "registros-propiedad",
    label: "Registros de propiedad",
    queryKey: "memoria-snapshot-registros",
    queryFn: getRegistrosPropiedadSnapshot,
    homePath: "/registros-propiedad",
  },
  {
    key: "articulos-divulgacion",
    label: "Artículos de divulgación",
    queryKey: "memoria-snapshot-articulos",
    queryFn: getArticulosDivulgacionSnapshot,
    homePath: "/articulos-divulgacion",
  },
  {
    key: "visitas-academicas",
    label: "Visitas académicas",
    queryKey: "memoria-snapshot-visitas",
    queryFn: getVisitasAcademicasSnapshot,
    homePath: "/visitantes",
  },
];

function buildMemoriaLabel(memoria: Memoria | null | undefined) {
  return memoria ? `Memoria ${formatFecha(memoria.periodo_inicio)}–${formatFecha(memoria.periodo_fin)}` : "Memoria";
}

const snapshotEntityIdKeys: Record<string, string> = {
  investigadores: "investigador_id",
  becarios: "becario_id",
  personal: "personal_id",
  proyectos: "proyecto_investigacion_id",
  "actividades-docencia": "actividad_docencia_id",
  "participaciones-relevantes": "participacion_relevante_id",
  "documentacion-bibliografica": "documentacion_bibliografica_id",
  equipamiento: "equipamiento_id",
  erogaciones: "movimiento_id",
  transferencias: "transferencia_id",
  "trabajos-reunion-cientifica": "trabajo_reunion_id",
  "trabajos-revistas": "trabajo_revista_id",
  distinciones: "distincion_id",
  "registros-propiedad": "registro_propiedad_id",
  "articulos-divulgacion": "articulo_divulgacion_id",
  "visitas-academicas": "visita_academica_id",
};

function getSnapshotEntityId(
  sectionKey: string,
  entry: MemoriaSnapshotEntry
): unknown {
  const mappedKey = snapshotEntityIdKeys[sectionKey];

  if (mappedKey && entry?.[mappedKey] !== undefined && entry?.[mappedKey] !== null) {
    return entry[mappedKey];
  }

  return entry?.id;
}

export default function MemoriaVersionDetalle() {
  const { id, versionId } = useParams<{ id: string; versionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAdmin, isGestor, canEditRecords } = useAuth();


  const memoriaId = Number(id);
  const memoriaVersionId = Number(versionId);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showError, setShowError] = useState(false);
  const [message, setMessage] = useState("");
  const [showProgramaModal, setShowProgramaModal] = useState(false);
  const programaDialogRef = useRef<HTMLDialogElement>(null);
  const [programaDescripcion, setProgramaDescripcion] = useState("");
  const [programaError, setProgramaError] = useState("");
  const exportInFlight = useRef(false);

  const { data: memoria, isLoading: isLoadingMemoria } = useQuery({
    queryKey: ["memoria", id],
    queryFn: () => getMemoriaById(memoriaId),
    enabled: Number.isFinite(memoriaId),
  });

  const snapshotQueries = useQueries({
    queries: sections.map((section) => ({
      queryKey: [section.queryKey, memoriaId, memoriaVersionId],
      queryFn: () => section.queryFn(memoriaId, memoriaVersionId),
      enabled: Number.isFinite(memoriaId) && Number.isFinite(memoriaVersionId),
    })),
  });

  const isLoadingSnapshots = snapshotQueries.some((query) => query.isLoading);

  const sectionData = useMemo(
    () =>
      sections.map((section, index) => ({
        ...section,
        items: snapshotQueries[index].data || [],
      })),
    [snapshotQueries]
  );
  const versionActual = (memoria?.versiones || []).find(
    (version) => version.id === memoriaVersionId
  );
  const versionCerrada = versionActual?.estado === "cerrada";
  const sectionsWithItems = sectionData.filter((section) => section.items.length > 0);
  const numeroVersionMemoria = versionActual?.numero_version ?? memoriaVersionId;
  const puedeExportarExcel = versionCerrada && (isAdmin() || isGestor());
  const anioFinMemoria = getCivilYear(memoria?.periodo_fin);
  const anioPrograma = anioFinMemoria ? anioFinMemoria + 1 : undefined;
  const puedeEditarPrograma = versionCerrada && canEditRecords();
  const descripcionProgramaInvalida = Boolean(programaError && !programaDescripcion.trim());

  const { data: planificacionesPage, isLoading: isLoadingPlanificaciones } = useQuery({
    queryKey: ["planificaciones", "true"],
    queryFn: () => getPlanificaciones("true"),
    enabled: puedeEditarPrograma && !!anioPrograma && !!memoria?.grupo_utn_id,
  });
  const planificaciones = planificacionesPage?.data ?? [];

  const planificacionActual = useMemo<PlanificacionGrupo | undefined>(
    () =>
      planificaciones.find(
        (item) => item.anio === anioPrograma && item.grupo_id === memoria?.grupo_utn_id && item.activo
      ),
    [anioPrograma, planificaciones, memoria?.grupo_utn_id]
  );

  useEffect(() => {
    if (!showProgramaModal) return;
    setProgramaDescripcion(planificacionActual?.descripcion ?? "");
    setProgramaError("");
  }, [planificacionActual, showProgramaModal]);

  useEffect(() => {
    const dialog = programaDialogRef.current;
    if (!showProgramaModal || !dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    dialog.querySelector<HTMLElement>("textarea")?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (opener?.isConnected) opener.focus();
    };
  }, [showProgramaModal]);

  const { mutate: descargarExcel, isPending: isExportingExcel } = useMutation({
    mutationFn: () => exportarExcelMemoria(memoriaId, memoriaVersionId),
    onSuccess: (result) => {
      setMessage(`Excel generado con éxito: ${result.filename}`);
      setShowSuccess(true);
    },
    onError: (error) => {
      setMessage(
        error instanceof Error
          ? error.message
          : "No se pudo generar el Excel de la memoria."
      );
      setShowError(true);
    },
    onSettled: () => {
      exportInFlight.current = false;
    },
  });

  const startExport = () => {
    if (exportInFlight.current || isExportingExcel) return;
    exportInFlight.current = true;
    descargarExcel();
  };

  const { mutate: guardarPrograma, isPending: isSavingPrograma } = useMutation({
    mutationFn: async () => {
      const descripcion = programaDescripcion.trim();
      if (!descripcion) {
        throw new Error("Debe ingresar una descripción para el programa de actividades.");
      }
      if (!anioPrograma || !memoria?.grupo_utn_id) {
        throw new Error("No se pudo resolver el año o el grupo de investigación.");
      }

      if (planificacionActual) {
        return updatePlanificacion(planificacionActual.id, {
          descripcion,
          anio: anioPrograma,
          grupo_id: memoria!.grupo_utn_id!,
        });
      }

      return createPlanificacion({
        descripcion,
        anio: anioPrograma,
        grupo_id: memoria!.grupo_utn_id!,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["planificaciones"] });
      setShowProgramaModal(false);
      setProgramaError("");
      setMessage(
        planificacionActual
          ? "Programa de actividades actualizado con éxito."
          : "Programa de actividades guardado con éxito."
      );
      setShowSuccess(true);
    },
    onError: (error) => {
      const nextMessage =
        error instanceof Error
          ? error.message
          : "No se pudo guardar el programa de actividades.";
      setProgramaError(nextMessage);
    },
  });

  const handleNavigateToSection = (section: SnapshotSection) => {
    if (!section.homePath) return;

    const entries = sectionData.find((current) => current.key === section.key)?.items ?? [];
    const ids = entries
      .map((entry) => getSnapshotEntityId(section.key, entry))
      .filter((value: unknown) => value !== undefined && value !== null);

    navigate(section.homePath, {
      state: {
        memoriaFilter: {
          source: "memoria",
          sectionKey: section.key,
          sectionLabel: section.label,
          ids,
          memoriaLabel: buildMemoriaLabel(memoria),
          memoriaId,
          versionId: memoriaVersionId,
        },
      },
    });
  };

  const abrirProgramaActividades = () => {
    if (!memoria?.grupo_utn_id) {
      setMessage("No hay un grupo de investigación configurado para guardar la planificación.");
      setShowError(true);
      return;
    }
    setShowProgramaModal(true);
  };

  const handleGuardarPrograma = () => {
    if (!programaDescripcion.trim()) {
      setProgramaError("Debe ingresar una descripción para el programa de actividades.");
      return;
    }
    guardarPrograma();
  };

  if (isLoadingMemoria) {
    return <LoadingSkeleton variant="detail" label="Cargando memoria..." />;
  }

  if (!memoria) {
    return <p className="text-slate-500">No se encontró la memoria.</p>;
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold leading-none md:text-3xl">
            Elementos registrados
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Memoria {formatFecha(memoria.periodo_inicio)} - {formatFecha(memoria.periodo_fin)}
          </p>
          <p className="mt-1 text-xs text-slate-500">Versión {numeroVersionMemoria}</p>
          <p className="mt-1 text-sm text-slate-500">UCT: {memoria.grupo_utn_nombre || "Pendiente de asociar"}</p>
        </div>

        <div className="flex items-center gap-2">
          {puedeEditarPrograma && (
            <Button
              size="sm"
              variant="secondary"
              onClick={abrirProgramaActividades}
              disabled={isLoadingPlanificaciones}
            >
              Planificación actual
            </Button>
          )}

          {puedeExportarExcel && (
            <Button size="sm" onClick={startExport} disabled={isExportingExcel} loading={isExportingExcel} loadingText="Generando el archivo...">
              Generar Excel
            </Button>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate(`/memorias/${memoria.id}`)}
          >
            Volver
          </Button>
        </div>
      </div>

      {isLoadingSnapshots ? (
        <LoadingSkeleton variant="table" label="Cargando elementos registrados…" />
      ) : !versionCerrada ? (
        <div className="flex flex-col gap-6">
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
            Esta versión aún no fue cerrada. Los elementos registrados estarán
            disponibles una vez generado el snapshot al cerrar la memoria.
          </div>

          <div className="flex justify-start">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate(`/memorias/${memoria.id}`)}
            >
              Volver
            </Button>
          </div>
        </div>
      ) : sectionsWithItems.length === 0 ? (
        <div className="flex flex-col gap-6">
          <div className="rounded-2xl border border-slate-200 bg-white/90 px-5 py-6 text-sm text-slate-500 shadow-sm">
            Esta versión no contiene elementos registrados.
          </div>

          <div className="flex justify-start">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate(`/memorias/${memoria.id}`)}
            >
              Volver
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sectionsWithItems.map((section) => (
              <article
                key={section.key}
                className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">
                      {section.label}
                    </h3>
                    <p className="mt-1 text-xs uppercase tracking-wider text-slate-400">
                      {section.items.length} registrados
                    </p>
                  </div>

                  <span
                    className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
                      section.items.length > 0
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {section.items.length > 0 ? "Disponible" : "Sin datos"}
                  </span>
                </div>

                <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3">
                  <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                    <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
                      Cantidad registrada
                    </p>
                    <p className="mt-2 text-3xl font-semibold text-slate-800">
                      {section.items.length}
                    </p>
                    <p className="mt-2 text-sm text-slate-500">
                      Esta sección aporta {section.items.length} elemento
                      {section.items.length === 1 ? "" : "s"} al snapshot de esta
                      versión.
                    </p>
                  </div>
                </div>

                {section.items.length > 0 && section.homePath && (
                  <button
                    type="button"
                    onClick={() => handleNavigateToSection(section)}
                    className="mt-3 text-xs font-semibold uppercase tracking-wider text-slate-500 transition-colors hover:text-slate-700"
                  >
                    Ver registros en el módulo
                  </button>
                )}
              </article>
            ))}
          </div>

          <div className="flex justify-start">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate(`/memorias/${memoria.id}`)}
            >
              Volver
            </Button>
          </div>
        </div>
      )}

      <SuccessToast
        open={showSuccess}
        message={message}
        onClose={() => setShowSuccess(false)}
      />

      <SuccessToast
        open={showError}
        message={message}
        onClose={() => setShowError(false)}
        variant="error"
      />

      {showProgramaModal && (
        <dialog
          ref={programaDialogRef}
          aria-labelledby="programa-actividades-title"
          aria-describedby="programa-actividades-description"
          onCancel={(event) => { event.preventDefault(); if (!isSavingPrograma) setShowProgramaModal(false); }}
          onClick={(event) => {
            if (event.target !== event.currentTarget || isSavingPrograma) return;
            const rect = event.currentTarget.getBoundingClientRect();
            if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) setShowProgramaModal(false);
          }}
          className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-2xl rounded-2xl border border-slate-200 bg-white/95 p-6 shadow-lg backdrop:bg-black/30 backdrop:backdrop-blur-sm"
        >
            <div className="mb-4">
              <h3 id="programa-actividades-title" className="text-lg font-semibold text-slate-900">
                Programa de Actividades {anioPrograma ?? ""}
              </h3>
              <p id="programa-actividades-description" className="mt-1 text-sm text-slate-500">
                Registra los objetivos y actividades actuales del grupo para el año siguiente al fin del período. Los cambios no modifican los datos históricos ni el Excel de esta versión cerrada.
              </p>
            </div>

            <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <span className="font-medium text-slate-700">Período:</span>{" "}
              {anioPrograma ?? "-"}
            </div>

            <label htmlFor="programa-actividades-descripcion" className="block text-sm font-medium text-slate-700">
              Descripción
            </label>
            <textarea
              id="programa-actividades-descripcion"
              rows={10}
              aria-invalid={descripcionProgramaInvalida}
              aria-describedby={descripcionProgramaInvalida ? "programa-actividades-descripcion-error" : undefined}
              className={`mt-2 w-full rounded-xl border bg-white px-4 py-3 text-sm text-slate-800 outline-none transition ${
                descripcionProgramaInvalida
                  ? "border-red-400 ring-2 ring-red-200"
                  : "border-slate-200 focus:border-slate-400"
              }`}
              value={programaDescripcion}
              placeholder="Ej: objetivos, actividades previstas, líneas de trabajo, cronograma y metas del grupo para el próximo período."
              onChange={(e) => {
                setProgramaDescripcion(e.target.value);
                if (programaError) setProgramaError("");
              }}
            />
            {programaError && (
              <p id="programa-actividades-descripcion-error" role="alert" className="mt-2 text-sm text-red-500">{programaError}</p>
            )}

            <div className="mt-6 flex justify-between gap-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowProgramaModal(false)}
                disabled={isSavingPrograma}
              >
                Cancelar
              </Button>

              <Button size="sm" onClick={handleGuardarPrograma} disabled={isSavingPrograma} loading={isSavingPrograma} loadingText="Guardando...">
                {isSavingPrograma ? "Guardando..." : planificacionActual ? "Actualizar" : "Guardar"}
              </Button>
            </div>
        </dialog>
      )}
    </section>
  );
}
