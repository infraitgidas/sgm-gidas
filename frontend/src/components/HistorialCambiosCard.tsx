import { useEffect, useMemo, useState } from "react";
import Button from "@/components/Button";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import { formatFechaHora } from "@/utils/dateTime";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export type HistorialCambioCardItem = {
  id: number | string;
  campo?: string;
  fecha_cambio?: string | null;
  usuario_nombre?: string | null;
  valor_anterior?: unknown;
  valor_nuevo?: unknown;
  tipo?: string;
};

type HistorialCambioPresentation = {
  title: string;
  description: string;
};

type Props = {
  title?: string;
  subtitle?: string;
  items?: HistorialCambioCardItem[] | null;
  isLoading?: boolean;
  updatedAt?: string | null;
  updatedByName?: string | null;
  pageSize?: number;
  formatItemValue?: (
    item: HistorialCambioCardItem,
    value: unknown,
    kind: "anterior" | "nuevo"
  ) => string;
  formatItemPresentation?: (
    item: HistorialCambioCardItem
  ) => HistorialCambioPresentation | null;
};

function formatValor(valor: unknown) {
  if (valor === null || valor === undefined || valor === "") return "-";

  if (typeof valor === "object") {
    try {
      return JSON.stringify(valor);
    } catch {
      return "-";
    }
  }

  return String(valor);
}

function formatLabel(key?: string) {
  if (!key) return "Cambio";
  const normalizedKey = key.endsWith("_id") ? key.slice(0, -3) : key;
  return normalizedKey
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

export default function HistorialCambiosCard({
  title = "Historial de cambios",
  subtitle,
  items,
  isLoading = false,
  updatedAt,
  updatedByName,
  pageSize = 3,
  formatItemValue,
  formatItemPresentation,
}: Props) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);

  const normalizedItems = useMemo(() => {
    const safeItems = Array.isArray(items) ? items : [];

    const updateItem = updatedAt
      ? [
          {
            id: "ultima-actualizacion",
            tipo: "ultima_actualizacion",
            fecha_cambio: updatedAt,
            usuario_nombre: updatedByName || "-",
          } satisfies HistorialCambioCardItem,
        ]
      : [];

    return [...updateItem, ...safeItems];
  }, [items, updatedAt, updatedByName]);

  const totalPages = Math.max(1, Math.ceil(normalizedItems.length / pageSize));

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  useEffect(() => {
    setPage(1);
  }, [items, updatedAt, updatedByName]);

  const paginatedItems = normalizedItems.slice(
    (page - 1) * pageSize,
    page * pageSize
  );

  const renderItem = (item: HistorialCambioCardItem) => {
    if (item.tipo === "ultima_actualizacion") {
      return (
        <div
          key={`${item.id}-${item.fecha_cambio ?? "sin-fecha"}`}
          className="rounded-xl border border-slate-200 bg-white px-4 py-3"
        >
          <div className="space-y-1 text-sm text-slate-500">
            <p className="font-medium text-slate-700">Última actualización</p>
            <p>
              <span className="font-medium text-slate-700">Fecha:</span>{" "}
              {formatFechaHora(item.fecha_cambio)}
            </p>
            <p>
              <span className="font-medium text-slate-700">Usuario:</span>{" "}
              {item.usuario_nombre || "-"}
            </p>
          </div>
        </div>
      );
    }

    const presentation = formatItemPresentation?.(item);
    if (presentation) {
      return (
        <div
          key={`${item.id}-${item.fecha_cambio ?? "sin-fecha"}`}
          className="rounded-xl border border-slate-200 bg-white px-4 py-3"
        >
          <div className="space-y-1 text-sm text-slate-500">
            <p className="font-medium text-slate-700">{presentation.title}</p>
            <p>{presentation.description}</p>
            <p>
              <span className="font-medium text-slate-700">Fecha:</span>{" "}
              {formatFechaHora(item.fecha_cambio)}
            </p>
            <p>
              <span className="font-medium text-slate-700">Usuario:</span>{" "}
              {item.usuario_nombre || "-"}
            </p>
          </div>
        </div>
      );
    }

    const titulo =
      item.tipo === "historial_grado"
        ? "Historial de grado academico"
        : formatLabel(item.campo);

    const valorAnterior = formatItemValue
      ? formatItemValue(item, item.valor_anterior, "anterior")
      : formatValor(item.valor_anterior);
    const valorNuevo = formatItemValue
      ? formatItemValue(item, item.valor_nuevo, "nuevo")
      : formatValor(item.valor_nuevo);

    return (
      <div
        key={`${item.id}-${item.fecha_cambio ?? "sin-fecha"}`}
        className="rounded-xl border border-slate-200 bg-white px-4 py-3"
      >
        <div className="space-y-1 text-sm text-slate-500">
          <p className="font-medium text-slate-700">{titulo}</p>
          <p>
            <span className="font-medium text-slate-700">Fecha:</span>{" "}
            {formatFechaHora(item.fecha_cambio)}
          </p>
          <p>
            <span className="font-medium text-slate-700">Usuario:</span>{" "}
            {item.usuario_nombre || "-"}
          </p>
          <p>
            <span className="font-medium text-slate-700">Valor anterior:</span>{" "}
            {valorAnterior}
          </p>
          <p>
            <span className="font-medium text-slate-700">Valor nuevo:</span>{" "}
            {valorNuevo}
          </p>
        </div>
      </div>
    );
  };

  return (
    <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6 shadow-sm">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-center justify-between text-left"
          >
            <div>
              <h3 className="text-lg font-semibold text-slate-700">{title}</h3>
              {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
            </div>
            <span className="text-sm text-slate-500">
              {open ? "Ocultar" : "Ver historial"}
            </span>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent className="pt-4">
          {isLoading ? (
            <LoadingSkeleton variant="compact" label="Cargando historial…" />
          ) : normalizedItems.length === 0 ? (
            <p className="text-sm text-slate-500">No hay cambios registrados.</p>
          ) : (
            <div className="space-y-3">
              {paginatedItems.map(renderItem)}

              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                    disabled={page === 1}
                  >
                    Anterior
                  </Button>

                  <span className="text-sm text-slate-500">
                    Página {page} de {totalPages}
                  </span>

                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      setPage((prev) => Math.min(totalPages, prev + 1))
                    }
                    disabled={page === totalPages}
                  >
                    Siguiente
                  </Button>
                </div>
              )}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </article>
  );
}
