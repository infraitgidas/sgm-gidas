import { useEffect, useId, useRef, useState } from "react";
import Button from "@/components/Button";
import Table, { type TableColumn } from "@/components/Table";
import { formatFecha } from "@/utils/dateTime";
import type { MemoriaSnapshotEntry } from "@/modules/memorias/services/memoriasService";

interface Props {
  sectionKey: string;
  title: string;
  versionLabel: string;
  items: MemoriaSnapshotEntry[];
  onClose: () => void;
}

const text = (value: unknown) => typeof value === "string" && value.trim() ? value : "Sin dato";

export default function PersonalSnapshotDialog({ sectionKey, title, versionLabel, items, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  const [page, setPage] = useState(1);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    closeRef.current?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (opener?.isConnected) opener.focus();
    };
  }, []);

  const columns: TableColumn<MemoriaSnapshotEntry>[] = [
    { id: "nombre", header: "Nombre y apellido", render: row => text(row.nombre_apellido) },
    { id: "clasificacion", header: sectionKey === "becarios" ? "Nivel de Formación" : sectionKey === "investigadores" ? "Tipo de Dedicación" : "Tipo de Personal",
      render: row => text(row[sectionKey === "becarios" ? "tipo_formacion_nombre" : sectionKey === "investigadores" ? "tipo_dedicacion_nombre" : "tipo_personal_nombre"]) },
    { id: "horas", header: "Horas semanales", render: row => typeof row.horas_semanales === "number" ? `${row.horas_semanales} h` : "Sin dato" },
    { id: "alta", header: "Fecha de alta", render: row => typeof row.fecha_alta_grupo === "string" ? formatFecha(row.fecha_alta_grupo) : "Sin dato" },
    { id: "grupo", header: "Grupo", render: row => text(row.grupo_utn_nombre) },
  ];
  if (sectionKey === "investigadores") columns.push(
    { id: "categoria", header: "Categoría UTN", render: row => text(row.categoria_utn_nombre) },
    { id: "programa", header: "Programa de incentivos", render: row => text(row.programa_incentivos_nombre) },
  );
  if (sectionKey === "becarios") columns.push(
    { id: "becas", header: "Becas", render: row => text(row.becas_percibidas) },
    { id: "fuentes", header: "Financiamiento", render: row => text(row.fuentes_financiamiento_beca) },
  );

  return <dialog ref={dialogRef} aria-labelledby={titleId} aria-describedby={descriptionId}
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => {
      if (event.target !== event.currentTarget) return;
      const rect = event.currentTarget.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose();
    }}
    className="fixed inset-0 m-auto max-h-[90vh] w-[calc(100%-2rem)] max-w-6xl overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-lg backdrop:bg-black/30 md:p-6">
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        <h3 id={titleId} className="text-lg font-semibold text-slate-900">{title} · {versionLabel}</h3>
        <p id={descriptionId} className="mt-2 text-sm text-slate-600">Datos guardados en esta versión. Los cambios posteriores del integrante no modifican esta información.</p>
      </div>
      <button ref={closeRef} type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium">Cerrar</button>
    </div>
    <Table caption={`${title} guardados en ${versionLabel}`} columns={columns} rows={items.slice((page - 1) * 9, page * 9)}
      getRowId={row => String(row.id)} page={page} totalPages={Math.max(1, Math.ceil(items.length / 9))}
      totalRecords={items.length} onPageChange={setPage} emptyMessage="Esta versión no contiene registros en esta sección." />
    <div className="mt-5 flex justify-end"><Button type="button" variant="secondary" onClick={onClose}>Volver a la versión</Button></div>
  </dialog>;
}
