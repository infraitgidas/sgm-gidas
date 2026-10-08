import { useRef, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { ChevronRight, Eye, Pencil, RotateCcw, X } from "lucide-react";
import LoadingSkeleton from "@/components/LoadingSkeleton";

export type TableSortDirection = "asc" | "desc";

export interface TableColumn<T> {
  id: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  align?: "left" | "center" | "right";
  priority?: "primary" | "secondary" | "tertiary";
  sortable?: boolean;
  sortKey?: string;
  headerClassName?: string;
  cellClassName?: string;
}

export interface TableProps<T> {
  caption: string;
  columns: TableColumn<T>[];
  rows: T[];
  getRowId: (row: T) => string | number;
  density?: "compact" | "comfortable";
  loading?: boolean;
  refreshing?: boolean;
  error?: boolean;
  loadingMessage?: string;
  emptyMessage?: string;
  errorMessage?: string;
  onRetry?: () => void;
  sortKey?: string;
  sortDirection?: TableSortDirection;
  onSortChange?: (key: string, direction: TableSortDirection) => void;
  expandedRowId?: string | number | null;
  isRowExpanded?: (row: T) => boolean;
  renderExpanded?: (row: T) => ReactNode;
  onToggleRow?: (row: T) => void;
  getExpandLabel?: (row: T, expanded: boolean) => string;
  onRowClick?: (row: T) => void;
  getRowTitle?: (row: T) => string;
  toolbar?: ReactNode;
  page: number;
  totalPages: number;
  totalRecords: number;
  onPageChange: (page: number) => void;
}

const alignClasses = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

const priorityClasses = {
  primary: "",
  secondary: "hidden md:table-cell",
  tertiary: "hidden xl:table-cell",
};

export function TableToolbar({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-3 border-b border-slate-200 p-4 lg:flex-row lg:items-center lg:justify-between">{children}</div>;
}

export function TableSearch({ label = "Buscar", ...props }: { label?: string } & Omit<React.InputHTMLAttributes<HTMLInputElement>, "type">) {
  return (
    <label className="relative block w-full lg:max-w-sm">
      <span className="sr-only">{label}</span>
      <input type="search" aria-label={label} className="input w-full" {...props} />
    </label>
  );
}

export function TableFilterChip({ active = false, children, className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium outline-none transition motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 ${active ? "border-slate-800 bg-slate-800 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function TableActions({ children }: { children: ReactNode }) {
  return <div className="flex items-center justify-end gap-1">{children}</div>;
}

export function TableActionButton({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" className={`rounded-lg px-2 py-1.5 text-xs font-medium text-slate-700 outline-none transition motion-reduce:transition-none hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 ${className}`} {...props} />;
}

export type TableRowAction = "view" | "edit" | "delete" | "restore";

const rowActionConfig = {
  view: { label: "Ver detalle", icon: Eye, className: "" },
  edit: { label: "Editar", icon: Pencil, className: "" },
  delete: { label: "Eliminar", icon: X, className: "text-rose-700 hover:bg-rose-50" },
  restore: { label: "Restaurar", icon: RotateCcw, className: "" },
} satisfies Record<TableRowAction, { label: string; icon: typeof Eye; className: string }>;

type TableRowActionButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  action: TableRowAction;
  label?: string;
};

export function TableRowActionButton({ action, label, className = "", title, ...props }: TableRowActionButtonProps) {
  const config = rowActionConfig[action];
  const Icon = config.icon;
  const visibleLabel = label ?? config.label;

  return (
    <TableActionButton
      title={title ?? visibleLabel}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap ${config.className} ${className}`}
      {...props}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
      <span>{visibleLabel}</span>
    </TableActionButton>
  );
}

export default function Table<T>({
  caption, columns, rows, getRowId, density = "comfortable", loading = false, refreshing = false,
  error = false, loadingMessage = "Cargando información…", emptyMessage = "No hay registros para mostrar.",
  errorMessage = "Lo sentimos, no pudimos recuperar la información. Intente nuevamente.", onRetry,
  sortKey, sortDirection = "asc", onSortChange, expandedRowId, isRowExpanded, renderExpanded,
  onToggleRow, getExpandLabel, onRowClick, getRowTitle, toolbar,
  page, totalPages, totalRecords, onPageChange,
}: TableProps<T>) {
  const padding = density === "compact" ? "px-3 py-2.5" : "px-4 py-4";
  const status = loading || error || rows.length === 0;
  const firstRowRef = useRef<HTMLTableRowElement>(null);
  const sortButtons = useRef<Record<string, HTMLButtonElement | null>>({});
  const [activeHeader, setActiveHeader] = useState<string | null>(null);
  const sortableIds = columns.filter((column) => column.sortable).map((column) => column.id);
  const tabStop = activeHeader && sortableIds.includes(activeHeader) ? activeHeader : sortableIds[0];

  const moveHeaderFocus = (event: React.KeyboardEvent<HTMLButtonElement>, id: string) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const visibleIds = sortableIds.filter((key) => sortButtons.current[key]?.getClientRects().length);
    if (!visibleIds.length) return;
    const current = visibleIds.indexOf(id);
    const next = event.key === "Home" ? 0 : event.key === "End" ? visibleIds.length - 1
      : (current + (event.key === "ArrowRight" ? 1 : -1) + visibleIds.length) % visibleIds.length;
    event.preventDefault();
    setActiveHeader(visibleIds[next]);
    sortButtons.current[visibleIds[next]]?.focus();
  };

  const focusFirstResult = () => {
    const firstRow = firstRowRef.current;
    const action = firstRow?.querySelector<HTMLElement>("button:not([disabled]), a[href], input:not([disabled])");
    (action ?? firstRow)?.focus();
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {toolbar}
      {!status && <button type="button" onClick={focusFirstResult} className="sr-only focus:not-sr-only focus:block focus:w-full focus:bg-sky-50 focus:px-4 focus:py-2 focus:text-left focus:text-sm focus:font-medium focus:text-sky-800">Saltar los encabezados e ir al primer resultado</button>}
      <div className="overflow-x-auto">
        <table aria-busy={loading || refreshing} className="w-full min-w-[760px] border-collapse text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
            <tr>
              {onToggleRow && <th scope="col" className={`w-10 ${padding}`}><span className="sr-only">Expandir fila</span></th>}
              {columns.map((column) => {
                const active = column.sortable && sortKey === (column.sortKey ?? column.id);
                const alignment = alignClasses[column.align ?? "left"];
                return (
                  <th key={column.id} scope="col" aria-sort={active ? (sortDirection === "asc" ? "ascending" : "descending") : column.sortable ? "none" : undefined}
                    className={`${padding} ${alignment} ${priorityClasses[column.priority ?? "primary"]} ${column.headerClassName ?? ""}`}>
                    {column.sortable ? (
                      <button type="button" ref={(node) => { sortButtons.current[column.id] = node; }} tabIndex={column.id === tabStop ? 0 : -1} onFocus={() => setActiveHeader(column.id)} onKeyDown={(event) => moveHeaderFocus(event, column.id)} className="inline-flex items-center gap-1 rounded outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-slate-500"
                        onClick={() => onSortChange?.(column.sortKey ?? column.id, active && sortDirection === "asc" ? "desc" : "asc")}>
                        {column.header}<span aria-hidden="true">{active ? (sortDirection === "asc" ? "↑" : "↓") : "↕"}</span>
                      </button>
                    ) : column.header}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className={`divide-y divide-slate-100 transition-opacity duration-200 motion-reduce:transition-none ${refreshing ? "opacity-60" : "opacity-100"}`}>
            {status ? (
              <tr><td colSpan={columns.length + (onToggleRow ? 1 : 0)} className="px-4 py-12 text-center text-slate-500">
                <div role={error ? "alert" : loading ? undefined : "status"} aria-live={loading ? undefined : "polite"}>
                  {loading ? <LoadingSkeleton variant="table" label={loadingMessage} /> : error ? errorMessage : emptyMessage}
                  {error && onRetry && <div className="mt-3"><TableActionButton onClick={onRetry} className="border border-slate-300">Reintentar</TableActionButton></div>}
                </div>
              </td></tr>
            ) : rows.map((row, index) => {
              const id = getRowId(row);
              const expanded = isRowExpanded
                ? isRowExpanded(row)
                : expandedRowId != null && String(expandedRowId) === String(id);
              return [
                <tr
                  key={String(id)}
                  ref={index === 0 ? firstRowRef : undefined}
                  tabIndex={index === 0 ? -1 : undefined}
                  title={onRowClick ? getRowTitle?.(row) ?? "Ver detalle" : undefined}
                  onClick={onRowClick ? (event) => {
                    const target = event.target;
                    if (target instanceof Element && target.closest("button, a, input, select, textarea, [role='button']")) return;
                    onRowClick(row);
                  } : undefined}
                  className={`transition-colors motion-reduce:transition-none hover:bg-slate-50/80 focus:outline focus:outline-2 focus:outline-sky-700 ${onRowClick ? "cursor-pointer" : ""}`}
                >
                  {onToggleRow && (
                    <td className={`${padding} w-10`}>
                      <button
                        type="button"
                        aria-expanded={expanded}
                        aria-label={getExpandLabel?.(row, expanded) ?? (expanded ? "Contraer fila" : "Expandir fila")}
                        title={expanded ? "Ocultar historial" : "Mostrar historial"}
                        onClick={() => onToggleRow(row)}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 outline-none transition motion-reduce:transition-none hover:bg-slate-200 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-1"
                      >
                        <ChevronRight aria-hidden="true" className={`h-4 w-4 transition-transform motion-reduce:transition-none ${expanded ? "rotate-90" : ""}`} />
                      </button>
                    </td>
                  )}
                  {columns.map((column) => <td key={column.id} className={`${padding} ${alignClasses[column.align ?? "left"]} ${priorityClasses[column.priority ?? "primary"]} ${column.cellClassName ?? ""}`}>{column.render(row)}</td>)}
                </tr>,
                expanded && renderExpanded ? <tr key={`${String(id)}-expanded`}><td colSpan={columns.length + (onToggleRow ? 1 : 0)} className="border-t border-slate-100 bg-slate-50/70 px-4 py-4">{renderExpanded(row)}</td></tr> : null,
              ];
            })}
          </tbody>
        </table>
      </div>
      {refreshing && <span className="sr-only" role="status" aria-live="polite">Actualizando resultados…</span>}
      {!loading && !error && totalRecords > 0 && (
        <div className="flex flex-col gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <span>{totalRecords} {totalRecords === 1 ? "registro" : "registros"}</span>
          <nav aria-label="Paginación de la tabla" className="flex items-center justify-center gap-1">
            <TableActionButton aria-label="Página anterior" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Anterior</TableActionButton>
            {Array.from({ length: totalPages }, (_, index) => index + 1).map((number) => (
              <button key={number} type="button" aria-label={`Página ${number}`} aria-current={page === number ? "page" : undefined}
                onClick={() => onPageChange(number)} className={`h-8 min-w-8 rounded-lg px-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-slate-500 ${page === number ? "bg-slate-800 text-white" : "hover:bg-slate-100"}`}>{number}</button>
            ))}
            <TableActionButton aria-label="Página siguiente" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Siguiente</TableActionButton>
          </nav>
        </div>
      )}
    </div>
  );
}
