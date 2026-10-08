import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Button from "@/components/Button";
import HistorialCambiosCard from "@/components/HistorialCambiosCard";
import SuccessToast from "@/components/SuccessToast";
import {
  getEquipamientoById,
  getHistorialEquipamientoById,
  type Equipamiento,
} from "@/modules/recursos/services/equipamientoServices";
import { formatFecha, formatFechaHora } from "@/utils/dateTime";
import { useAuditoria } from "@/modules/shared/hooks/useAuditoria";
import { useAuth } from "@/context/AuthContext";
import {
  navigateBackFromMemoriaContext,
  stripSuccessMessageState,
} from "@/lib/memoriaNavigation";

const fmtMoney = (n?: number) =>
  typeof n === "number"
    ? new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        maximumFractionDigits: 2,
      }).format(n)
    : "-";

export default function EquipamientoDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canEditRecords } = useAuth();

  const puedeEditar = canEditRecords();

  const { data, isLoading, isError } = useQuery<Equipamiento>({
    queryKey: ["equipamiento", id],
    queryFn: () => getEquipamientoById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const { data: historialCambios = [], isLoading: isLoadingHistorial } = useQuery({
    queryKey: ["equipamiento-historial", id],
    queryFn: () => getHistorialEquipamientoById(Number(id)),
    enabled: !!id,
    refetchOnMount: "always",
  });

  const auditoria = useAuditoria(data);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

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

  if (isLoading) return <LoadingSkeleton variant="detail" label="Cargando..." />;
  if (isError || !data) {
    return <p className="text-slate-500">No se encontró el equipamiento.</p>;
  }

  const isDeleted = !!data.deleted_at;

  return (
    <>
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-semibold leading-none md:text-3xl">
              {data.denominacion || "-"}
            </h2>

            <span
              className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
                isDeleted
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-emerald-200 bg-emerald-50 text-emerald-700"
              }`}
            >
              {isDeleted ? "INACTIVO" : "ACTIVO"}
            </span>
          </div>

          {puedeEditar && !isDeleted && (
            <Button
              size="sm"
              onClick={() => navigate(`/equipamiento/${data.id}/editar`)}
            >
              Editar
            </Button>
          )}
        </div>

        <article className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Descripción breve:</span>{" "}
              {data.descripcion_breve || "-"}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Fecha de incorporación:
              </span>{" "}
              {formatFecha(data.fecha_incorporacion)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Monto invertido:</span>{" "}
              {fmtMoney(data.monto_invertido)}
            </p>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Auditoría</h3>
            <p className="mt-1 text-xs text-slate-500">
              {data.denominacion || "-"}
            </p>
          </div>

          <div className="space-y-2 text-sm text-slate-500 md:text-base">
            <p>
              <span className="font-semibold text-slate-800">Creado por:</span>{" "}
              {data.created_by_nombre || auditoria.nombreCreador}
            </p>

            <p>
              <span className="font-semibold text-slate-800">
                Fecha de creación:
              </span>{" "}
              {formatFechaHora(data.created_at)}
            </p>

            <p>
              <span className="font-semibold text-slate-800">Eliminado por:</span>{" "}
              {data.deleted_by_nombre || auditoria.nombreEliminador}
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
          subtitle={data.denominacion || "-"}
          items={historialCambios}
          isLoading={isLoadingHistorial}
          updatedAt={data.updated_at}
          updatedByName={data.updated_by_nombre}
          formatItemValue={(item, value) => {
            if (item.campo === "monto_invertido") {
              if (value === null || value === undefined || value === "") return "-";
              return fmtMoney(Number(value));
            }

            if (item.campo === "fecha_incorporacion") {
              if (value === null || value === undefined || value === "") return "-";
              return formatFecha(String(value));
            }

            if (item.campo === "grupo_utn_id") {
              if (value === null || value === undefined || value === "") return "-";
              const idValue = Number(value);
              return idValue === data.grupo_utn_id ? data.grupo || `ID ${idValue}` : `ID ${idValue}`;
            }

            return value === null || value === undefined || value === ""
              ? "-"
              : String(value);
          }}
        />

        <div className="flex justify-start pt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigateBackFromMemoriaContext(navigate, location, "/equipamiento")
            }
          >
            Volver
          </Button>
        </div>
      </section>

      <SuccessToast
        open={showSuccess}
        message={successMessage}
        onClose={() => setShowSuccess(false)}
      />
    </>
  );
}
