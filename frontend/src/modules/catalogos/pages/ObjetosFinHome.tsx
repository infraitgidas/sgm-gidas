import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import Button from "@/components/Button";
import Tarjeta from "@/components/Tarjeta";
import ConfirmDialog from "@/components/ConfirmDialog";
import SuccessToast from "@/components/SuccessToast";

import {
  getErogaciones,
  deleteErogaciones,
  type Erogaciones,
} from "@/modules/recursos/services/erogacionesServices";
import {
  getEquipamiento,
  deleteEquipamiento,
  type Equipamiento,
} from "@/modules/recursos/services/equipamientoServices";

type Item =
  | (Erogaciones & { tipo: "Erogacion" })
  | (Equipamiento & { tipo: "Equipamiento" });

function formatearFecha(fecha?: string) {
  if (!fecha) return "-";
  const [y, m, d] = fecha.split("-");
  return `${d}/${m}/${y}`;
}

export default function ObjetosLanding() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showSuccess, setShowSuccess] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const { data: erogaciones = [], isLoading: loadingErog } = useQuery({
    queryKey: ["erogaciones"],
    queryFn: () => getErogaciones(),
    staleTime: 60_000,
  });

  const { data: equipamiento = [], isLoading: loadingEq } = useQuery({
    queryKey: ["equipamiento"],
    queryFn: () => getEquipamiento(),
    staleTime: 60_000,
  });

  const isLoading = loadingErog || loadingEq;

  const items: Item[] = [
    ...erogaciones.map((e) => ({ ...e, tipo: "Erogacion" as const })),
    ...equipamiento.map((e) => ({ ...e, tipo: "Equipamiento" as const })),
  ];

  const [selectMode, setSelectMode] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Item[]>([]);
  const [showConfirm, setShowConfirm] = useState(false);

  const toggleSelect = (item: Item, checked: boolean) => {
    setSelectedItems((prev) =>
      checked
        ? [...prev, item]
        : prev.filter((x) => !(x.tipo === item.tipo && x.id === item.id))
    );
  };

  const cancelSelection = () => {
    if (isDeleting) return;
    setSelectMode(false);
    setSelectedItems([]);
    setShowConfirm(false);
  };

  const confirmDelete = async () => {
    if (isDeleting) return;

    try {
      setIsDeleting(true);

      for (const item of selectedItems) {
        if (item.tipo === "Erogacion") {
          await deleteErogaciones(item.id);
        } else {
          await deleteEquipamiento(item.id);
        }
      }

      await qc.invalidateQueries({ queryKey: ["erogaciones"] });
      await qc.invalidateQueries({ queryKey: ["equipamiento"] });
      cancelSelection();
      setShowSuccess(true);
    } catch {
      setShowConfirm(false);
      setErrorMessage("No se pudo eliminar el elemento seleccionado.");
      setShowError(true);
    } finally {
      setIsDeleting(false);
    }
  };

  const confirmItemsText = selectedItems.map((item) =>
    item.tipo === "Erogacion"
      ? `Movimiento N.º ${String(item.numero_movimiento).padStart(6, "0")}`
      : item.denominacion
  );

  return (
    <section className="flex min-h-[calc(100vh-80px)] w-full flex-col px-4 py-2">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-semibold md:text-3xl">
          Objetos y Financiamiento
        </h2>

        {!selectMode ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSelectMode(true)}
          >
            Seleccionar
          </Button>
        ) : (
          <div className="flex gap-2">
            {selectedItems.length > 0 && (
              <Button size="sm" onClick={() => setShowConfirm(true)}>
                Eliminar
              </Button>
            )}
            <Button variant="secondary" size="sm" onClick={cancelSelection}>
              Cancelar
            </Button>
          </div>
        )}
      </div>

      <div className="flex-1">
        {isLoading && <LoadingSkeleton variant="table" label="Cargando objetos de financiamiento…" />}

        {!isLoading && items.length === 0 && (
          <p className="text-slate-500">
            Aún no hay erogaciones ni equipamientos cargados.
          </p>
        )}

        {!isLoading && items.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <Tarjeta<Item>
                key={`${item.tipo}-${item.id}`}
                item={item}
                title={() =>
                  item.tipo === "Erogacion"
                    ? `Movimiento N.º ${String(item.numero_movimiento).padStart(6, "0")}`
                    : item.denominacion
                }
                subtitle={() =>
                  item.tipo === "Erogacion"
                    ? `${item.tipo_movimiento === "INGRESO" ? "Ingreso" : "Egreso"} · ${item.monto} ${item.moneda}`
                    : formatearFecha(item.fecha_incorporacion)
                }
                selectable={selectMode}
                selected={selectedItems.some(
                  (x) => x.tipo === item.tipo && x.id === item.id
                )}
                onSelectChange={(checked) => toggleSelect(item, checked)}
                onClick={() =>
                  navigate(
                    item.tipo === "Erogacion"
                      ? `/movimientos/${item.id}`
                      : `/equipamiento/${item.id}`
                  )
                }
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={showConfirm}
        title="Eliminar items"
        message="Estas seguro de eliminar los siguientes elementos?"
        items={confirmItemsText}
        onCancel={cancelSelection}
        onConfirm={confirmDelete}
        confirmText={isDeleting ? "Eliminando..." : "Aceptar"}
        confirmDisabled={isDeleting}
       loadingText="Eliminando..."
     />

      <SuccessToast
        open={showSuccess}
        message="Eliminado con éxito."
        onClose={() => setShowSuccess(false)}
      />

      <SuccessToast
        open={showError}
        message={errorMessage}
        onClose={() => setShowError(false)}
        variant="error"
      />
    </section>
  );
}
