import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { ChevronDown } from "lucide-react";
import Button from "@/components/Button";
import SuccessToast from "@/components/SuccessToast";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import { formatFechaHora } from "@/utils/dateTime";
import {
  getHistorialPersonalByRolAndId,
  getPersonalCompletoByRolAndId,
} from "@/modules/personal/services/personalCompletoServices";
import type { HistorialHorasItem } from "@/modules/personal/services/personalCompletoServices";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { useAuth } from "@/context/AuthContext";
import { useTiposFormacion } from "@/modules/personal/hooks/useTiposFormacion";
import { useDedicaciones } from "@/modules/personal/hooks/useDedicaciones";
import { useCategoriasUtn } from "@/modules/catalogos/hooks/useCategoriasUtn";
import { useProgramasIncentivos } from "@/modules/grupo/hooks/useProgramasIncentivos";
import { useTiposPersonal } from "@/modules/personal/hooks/useTiposPersonal";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

export default function PersonalDetalle() {
  const { rol: paramRol, id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();
  const { data: tiposFormacion = [] } = useTiposFormacion();
  const { data: dedicaciones = [] } = useDedicaciones();
  const { data: categoriasUtn = [] } = useCategoriasUtn();
  const { data: programasIncentivos = [] } = useProgramasIncentivos();
  const { data: tiposPersonal = [] } = useTiposPersonal();

  const puedeEditar = canEditRecords();

  const rol = (() => {
    if (paramRol) return paramRol;
    const path = location.pathname;
    if (path.includes("/becarios/")) return "becario";
    if (path.includes("/investigadores/")) return "investigador";
    if (path.includes("/ptaa/")) return "personal";
    if (path.includes("/profesionales/")) return "profesional";
    return undefined;
  })();

  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showHistorialHoras, setShowHistorialHoras] = useState(false);

  useEffect(() => {
    if (location.state?.successMessage) {
      setSuccessMessage(location.state.successMessage);
      setShowSuccess(true);
      navigate(location.pathname, {
        replace: true,
        state: stripSuccessMessageState(location.state),
      });
    }
  }, [location.state, navigate, location.pathname]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["personal-detalle", rol, id],
    queryFn: () => getPersonalCompletoByRolAndId(rol!, Number(id)),
    enabled: !!rol && !!id,
  });

  const {
    data: historialCambios = [],
    isLoading: isLoadingHistorial,
  } = useQuery({
    queryKey: ["personal-historial", rol, id],
    queryFn: () => getHistorialPersonalByRolAndId(rol!, Number(id)),
    enabled: !!rol && !!id,
  });

  const auditoria = useAuditoria(data);
  const successAnnouncement = <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{successMessage}</p>;

  if (isLoading) {
    return <>{successAnnouncement}<LoadingSkeleton variant="detail" label="Cargando..." /></>;
  }

  if (isError || !data) {
    return <>{successAnnouncement}<p className="text-slate-500">No se encontró el registro.</p></>;
  }

  const relaciones = data.relaciones || {};
  const isInactive = !!data.deleted_at || data.activo === false;
  const nombreActualizador =
    typeof data.updated_by_nombre === "string" && data.updated_by_nombre.trim()
      ? data.updated_by_nombre
      : "-";

  const formatearLabel = (key: string) => {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (l: string) => l.toUpperCase());
  };

  const renderArray = (
    arr?: Array<{ nombre_apellido?: string; nombre?: string; titulo?: string }>
  ) => {
    if (!arr || arr.length === 0) return null;
    return arr
      .map((v) => v.nombre_apellido || v.nombre || v.titulo || "")
      .filter(Boolean)
      .join(", ");
  };

  const formatFecha = (fecha?: string | null) => {
    if (!fecha) return "Actual";
    const d = new Date(`${fecha}T00:00:00`);
    return d.toLocaleDateString("es-AR");
  };

  const getRolLabel = () => {
    if (rol === "personal") return "PTAA";
    if (rol === "profesional") return "Profesional";
    if (rol === "investigador") return "Investigador";
    if (rol === "becario") return "Becario";
    return rol ?? "-";
  };

  const handleEditar = () => {
    navigate(`/personal/${rol}/${id}/editar`);
  };

  const getCatalogName = (
    collection: Array<{ id: number; nombre: string }>,
    value: unknown
  ) => {
    const normalizedId =
      typeof value === "number"
        ? value
        : typeof value === "string" && value.trim() !== ""
          ? Number(value)
          : NaN;

    if (Number.isNaN(normalizedId)) {
      return null;
    }

    return collection.find((item) => item.id === normalizedId)?.nombre ?? null;
  };

  const formatHistorialValue = (item: { campo?: string }, value: unknown) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    switch (item.campo) {
      case "tipo_formacion_id":
        return getCatalogName(tiposFormacion, value) ?? String(value);
      case "tipo_dedicacion_id":
        return getCatalogName(dedicaciones, value) ?? String(value);
      case "categoria_utn_id":
        return getCatalogName(categoriasUtn, value) ?? String(value);
      case "programa_incentivos_id":
        return getCatalogName(programasIncentivos, value) ?? String(value);
      case "tipo_personal_id":
        return getCatalogName(tiposPersonal, value) ?? String(value);
      default:
        if (typeof value === "object") {
          try {
            return JSON.stringify(value);
          } catch {
            return "-";
          }
        }
        return String(value);
    }
  };

  return (
    <>
      {successAnnouncement}
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl md:text-3xl font-semibold leading-none">
              {data.nombre_apellido ?? "Detalle"}
            </h2>

            <div className="flex flex-wrap items-center gap-2">
              {rol && (
                <span className="w-fit rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-600">
                  {getRolLabel()}
                </span>
              )}

              <span
                className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                  isInactive
                    ? "bg-red-100 text-red-700"
                    : "bg-emerald-100 text-emerald-700"
                }`}
              >
                {isInactive ? "INACTIVO" : "ACTIVO"}
              </span>
            </div>
          </div>

          {puedeEditar && !isInactive && (
            <Button size="sm" onClick={handleEditar}>
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p><span className="font-semibold text-slate-800">DNI:</span> {data.dni || "Sin registrar"}</p>
            <p><span className="font-semibold text-slate-800">CUIL:</span> {data.cuil || "Sin registrar"}</p>
            {relaciones.tipo_personal?.nombre && (
              <p>
                <span className="font-semibold text-slate-800">
                  Tipo de Personal:
                </span>{" "}
                {relaciones.tipo_personal.nombre}
              </p>
            )}

            {relaciones.tipo_formacion?.nombre && (
              <p>
                <span className="font-semibold text-slate-800">
                  Grado de Formación:
                </span>{" "}
                {relaciones.tipo_formacion.nombre}
              </p>
            )}

            {relaciones.categoria_utn?.nombre && (
              <p>
                <span className="font-semibold text-slate-800">
                  Categoría UTN:
                </span>{" "}
                {relaciones.categoria_utn.nombre}
              </p>
            )}

            {relaciones.programa_incentivos?.nombre && (
              <p>
                <span className="font-semibold text-slate-800">
                  Programa de Incentivos:
                </span>{" "}
                {relaciones.programa_incentivos.nombre}
              </p>
            )}

            {relaciones.tipo_dedicacion?.nombre && (
              <p>
                <span className="font-semibold text-slate-800">
                  Tipo de Dedicacion:
                </span>{" "}
                {relaciones.tipo_dedicacion.nombre}
              </p>
            )}

            {(relaciones.proyectos?.length ?? 0) > 0 && (
              <p>
                <span className="font-semibold text-slate-800">Proyectos:</span>{" "}
                {renderArray(relaciones.proyectos)}
              </p>
            )}

            {(relaciones.actividades_docencia?.length ?? 0) > 0 && (
              <p>
                <span className="font-semibold text-slate-800">
                  Actividades de Docencia:
                </span>{" "}
                {renderArray(relaciones.actividades_docencia)}
              </p>
            )}

            {(relaciones.trabajos_reunion_cientifica?.length ?? 0) > 0 && (
              <p>
                <span className="font-semibold text-slate-800">
                  Trabajos en Reunión Científica:
                </span>{" "}
                {renderArray(relaciones.trabajos_reunion_cientifica)}
              </p>
            )}

            {(relaciones.participaciones_relevantes?.length ?? 0) > 0 && (
              <p>
                <span className="font-semibold text-slate-800">
                  Participaciones Relevantes:
                </span>{" "}
                {renderArray(relaciones.participaciones_relevantes)}
              </p>
            )}

            {"horas_semanales" in data && (
              <div className="flex flex-col gap-2">
                <p className="flex items-center gap-2">
                  <span className="font-semibold text-slate-800">
                    Horas Semanales:
                  </span>
                  {data.horas_semanales}
                  {Array.isArray(data.historial_horas) &&
                    data.historial_horas.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowHistorialHoras((prev) => !prev)}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-100 hover:text-slate-800"
                        title="Ver historial de horas"
                        aria-label="Ver historial de horas"
                      >
                        <ChevronDown
                          className={`h-4 w-4 transition-transform ${
                            showHistorialHoras ? "rotate-180" : ""
                          }`}
                        />
                      </button>
                    )}
                </p>

                {showHistorialHoras &&
                  Array.isArray(data.historial_horas) &&
                  data.historial_horas.length > 0 && (
                    <div className="ml-4 space-y-1 border-l border-slate-200 pl-4 text-sm text-slate-600">
                      {data.historial_horas.map((h: HistorialHorasItem) => (
                        <p key={h.id}>
                          Horas: {h.horas_semanales} - Período:{" "}
                          {formatFecha(h.fecha_inicio)} - {formatFecha(h.fecha_fin)}
                        </p>
                      ))}
                    </div>
                  )}
              </div>
            )}

            {Array.isArray(data.becas) && (
              <div className="flex flex-col gap-2">
                <p>
                  <span className="font-semibold text-slate-800">Becas:</span>{" "}
                  {data.becas.length === 0 ? "No percibe beca" : ""}
                </p>

                {data.becas.length > 0 && (
                  <div className="ml-4 space-y-2 border-l border-slate-200 pl-4 text-sm text-slate-600">
                    {data.becas.map((b, index: number) => (
                      <div key={b.id ?? index}>
                        <p>
                          <span className="font-semibold text-slate-800">
                            {b.nombre_beca}
                          </span>
                        </p>
                        <p>
                          {formatFecha(b.fecha_inicio)} - {formatFecha(b.fecha_fin)}
                        </p>
                        <p>
                          Monto percibido:{" "}
                          {b.monto_percibido !== null &&
                          b.monto_percibido !== undefined
                            ? b.monto_percibido
                            : "-"}
                        </p>
                        {b.descripcion && <p>{b.descripcion}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {Object.entries(data)
              .filter(
                ([key, value]) =>
                  ![
                    "id",
                    "nombre_apellido",
                    "dni",
                    "cuil",
                    "identidad_id",
                    "activo",
                    "rol",
                    "relaciones",
                    "grupo",
                    "created_by",
                    "updated_by",
                    "deleted_by",
                    "created_by_nombre",
                    "updated_by_nombre",
                    "deleted_by_nombre",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                    "historial_horas",
                    "horas_semanales",
                    "becas",
                  ].includes(key) &&
                  value !== null &&
                  typeof value !== "object"
              )
              .map(([key, value]) => {
                if (key.endsWith("_id")) {
                  const relacionKey = key.replace("_id", "");
                  const relacion = Object.entries(relaciones).find(
                    ([nombre]) => nombre === relacionKey
                  )?.[1];
                  const nombreRelacion =
                    relacion && !Array.isArray(relacion) ? relacion.nombre : null;

                  if (nombreRelacion) {
                    return (
                      <p key={key}>
                        <span className="font-semibold text-slate-800">
                          {formatearLabel(relacionKey)}:
                        </span>{" "}
                        {nombreRelacion}
                      </p>
                    );
                  }
                  return null;
                }

                return (
                  <p key={key}>
                    <span className="font-semibold text-slate-800">
                      {formatearLabel(key)}:
                    </span>{" "}
                    {String(value) ?? "-"}
                  </p>
                );
              })}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
            <p className="mt-1 text-xs text-slate-500">{data.nombre_apellido}</p>
          </div>

          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Creado por:</span>{" "}
              {auditoria.nombreCreador}
            </p>
            <p>
              <span className="font-semibold text-slate-800">
                Fecha de creación:
              </span>{" "}
              {formatFechaHora(data.created_at)}
            </p>
            <p>
              <span className="font-semibold text-slate-800">Eliminado por:</span>{" "}
              {auditoria.nombreEliminador}
            </p>
            <p>
              <span className="font-semibold text-slate-800">
                Fecha de eliminación:
              </span>{" "}
              {formatFechaHora(data.deleted_at)}
            </p>
          </div>
        </article>

        <HistorialCambiosCard
          subtitle={data.nombre_apellido}
          items={historialCambios}
          isLoading={isLoadingHistorial}
          updatedAt={data.updated_at}
          updatedByName={nombreActualizador}
          formatItemValue={(item, value) => formatHistorialValue(item, value)}
        />

        <div className="flex justify-start pt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigateBackFromMemoriaContext(navigate, location, "/personal")
            }
          >
            Volver
          </Button>
        </div>
      </section>

      <SuccessToast
        open={showSuccess}
        message={successMessage}
        onClose={() => { setShowSuccess(false); setSuccessMessage(""); }}
      />
    </>
  );
}
