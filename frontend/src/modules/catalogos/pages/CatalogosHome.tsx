import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowUp,
  History,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import {
  createCatalogItem,
  deleteCatalogItem,
  getCatalogHistory,
  getCatalogItems,
  updateCatalogItem,
  type CatalogHistoryItem,
  type CatalogItem,
} from "@/modules/catalogos/services/catalogoServices";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import ErrorText from "@/components/ErrorText";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";
import { TableActionButton } from "@/components/Table";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage as getSafeErrorMessage } from "@/lib/httpError";
import { hasDescriptiveCatalogName } from "@/modules/catalogos/utils/catalogNameValidation";
import { hasOnlyLettersAndSpaces } from "@/lib/textValidation";

type StatusFilter = "all" | "active" | "inactive";

type FkField = {
  idField: string;
  label: string;
  endpoint: string;
  optionLabel?: string;
};

type CatalogDef = {
  label: string;
  endpoint: string;
  description: string;
  nameField?: string;
  descField?: string;
  fkField?: FkField;
};


type ToastState = {
  open: boolean;
  message: string;
  variant: "success" | "error";
};

type CatalogHistoryMap = Record<number, CatalogHistoryItem[]>;

const CATALOG_ITEMS_PER_PAGE = 9;
const HISTORY_ITEMS_PER_PAGE = 3;

function scrollToPageTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

const CATALOGS: CatalogDef[] = [
  {
    label: "Tipo de Personal",
    endpoint: "/tipo-personal/",
    description: "Clasifica personas dentro de la estructura del sistema.",
  },
  {
    label: "Nivel de Formación",
    endpoint: "/tipo-formacion/",
    description: "Clasifica la formación asociada a becarios.",
  },
  {
    label: "Categoría UTN",
    endpoint: "/categoria-utn/",
    description: "Define categorías institucionales de investigadores.",
  },
  {
    label: "Tipo de Dedicación",
    endpoint: "/tipo-dedicacion/",
    description: "Define dedicaciones usadas por investigadores.",
  },
  {
    label: "Grado Académico",
    endpoint: "/grado-academico",
    description: "Define grados académicos usados en actividades docentes.",
  },
  {
    label: "Programa de Incentivos",
    endpoint: "/programas-incentivos/",
    description: "Define programas asociados a investigadores.",
  },
  {
    label: "Cargos",
    endpoint: "/cargos/",
    description: "Define cargos usados en autoridades y directivos del grupo.",
  },
  {
    label: "Tipo de Proyecto",
    endpoint: "/tipos-proyecto/",
    description: "Clasifica proyectos de investigación.",
  },
  {
    label: "Rol de Actividad",
    endpoint: "/rol-actividad",
    description: "Clasifica el rol ocupado en actividades docentes.",
  },
  {
    label: "Tipo de Reunión Científica",
    endpoint: "/tipos-reunion-cientifica/",
    description: "Clasifica reuniones científicas para trabajos presentados.",
  },
  {
    label: "Tipo de Visita",
    endpoint: "/grupo/tipos-visita/",
    description: "Clasifica el propósito de las visitas, sin confundirlo con su procedencia.",
  },
  {
    label: "Tipo de Revista",
    endpoint: "/tipos-revista/",
    description: "Clasifica el alcance nacional o internacional de las revistas.",
  },
  {
    label: "Autores de documentación bibliográfica",
    endpoint: "/autores/",
    description: "Administra los autores de documentación bibliográfica. También puede añadir autores desde el formulario de Documentación.",
    nameField: "nombre_apellido",
  },
  {
    label: "Fuente de Financiamiento",
    endpoint: "/fuente-financiamiento/",
    description: "Define el origen de fondos usado en becas, proyectos y erogaciones.",
  },
  {
    label: "Tipo de Contrato",
    endpoint: "/tipo-contrato/",
    description: "Clasifica contratos usados en transferencias socio-productivas.",
  },
  {
    label: "Adoptantes",
    endpoint: "/adoptantes",
    description: "Administra los adoptantes disponibles para transferencias. Puede añadir adoptantes nuevos desde el formulario de transferencia.",
  },
  {
    label: "Tipo de Registro Propiedad",
    endpoint: "/tipo-registro-propiedad/",
    description: "Clasifica registros de propiedad intelectual e industrial.",
  },
];

function normalizeText(text: string) {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function formatEntityName(entityName: string) {
  return entityName
    .replace(/^el registro de\s+/i, "")
    .replace(/^la\s+/i, "")
    .replace(/^el\s+/i, "")
    .trim();
}

function isInactive(item: CatalogItem) {
  if (typeof item.activo === "boolean") return !item.activo;
  return Boolean(item.deleted_at);
}

function hasStatusData(item: CatalogItem) {
  return typeof item.activo === "boolean" || item.deleted_at !== undefined;
}

function formatDate(value: unknown) {
  if (typeof value !== "string" || !value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("es-AR");
}

function getModifiedAt(item: CatalogItem) {
  return (
    formatDate(item.updated_at) ||
    formatDate(item.created_at) ||
    formatDate(item.deleted_at)
  );
}

function getDeletedAt(item: CatalogItem) {
  return formatDate(item.deleted_at) || formatDate(item.updated_at);
}

function getDeletedBy(item: CatalogItem, history: CatalogHistoryItem[]) {
  const fromItem = item.deleted_by_nombre || item.deleter_name;
  if (typeof fromItem === "string" && fromItem.trim()) return fromItem;

  const deletionHistory = history.find((entry) => {
    if (entry.campo === "activo" && entry.valor_nuevo === false) return true;
    if (entry.campo !== "accion_sistema") return false;

    const payload = entry.valor_nuevo as { accion?: string } | null;
    return payload?.accion === "inactivar" || payload?.accion === "eliminar";
  });

  return deletionHistory?.usuario_nombre || "usuario no informado";
}

function getAuditLabel(item: CatalogItem, history: CatalogHistoryItem[]) {
  if (isInactive(item)) {
    const deletedAt = getDeletedAt(item);
    const deletedBy = getDeletedBy(item, history);
    return deletedAt
      ? `Eliminado ${deletedAt} por ${deletedBy}`
      : `Eliminado por ${deletedBy}`;
  }

  const modifiedAt = getModifiedAt(item);
  return modifiedAt ? `Modificado ${modifiedAt}` : "Sin fecha disponible";
}

function formatHistoryValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Vigente" : "Inactivo";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return "valor complejo";
    }
  }
  return String(value);
}

function formatHistoryItem(item: CatalogHistoryItem) {
  const date = formatDate(item.fecha_cambio) ?? "Sin fecha";
  const user = item.usuario_nombre ?? "Sistema";
  if (item.campo === "accion_sistema") {
    const payload = item.valor_nuevo as { accion?: string } | null;
    return `${date} - ${user} - ${payload?.accion ?? "acción registrada"}`;
  }

  const field = item.campo === "nombre_apellido" ? "Nombre y apellido" : item.campo === "activo" ? "Estado" : item.campo ?? "campo";
  return `${date} - ${user} - ${field}: ${formatHistoryValue(
    item.valor_anterior
  )} -> ${formatHistoryValue(item.valor_nuevo)}`;
}

function mapBackendMessage(
  rawMessage: string,
  action: "crear" | "actualizar" | "eliminar",
  entityName: string
) {
  const message = normalizeText(rawMessage);
  const cleanEntity = formatEntityName(entityName);

  if (message.includes("no encontrado")) {
    return `No se encontró el registro de ${cleanEntity}. Es posible que haya sido eliminado o que ya no esté disponible.`;
  }

  if (message.includes("es obligatorio") || message.includes("no puede estar vacio")) {
    return `Revise la información ingresada para poder ${action} ${cleanEntity}.`;
  }

  if (message.includes("ya existe")) {
    return `Ya existe un registro de ${cleanEntity} con ese nombre.`;
  }

  if (
    message.includes("asociad") ||
    message.includes("esta en uso") ||
    message.includes("esta siendo utilizado")
  ) {
    return `No se puede eliminar ${cleanEntity} porque tiene registros asociados.`;
  }

  if (message.includes("inactivo") || message.includes("eliminado")) {
    return `No se puede editar ${cleanEntity} porque está inactivo.`;
  }

  return null;
}

function getCatalogErrorMessage(
  error: unknown,
  action: "crear" | "actualizar" | "eliminar",
  entityName: string
) {
  const cleanEntity = formatEntityName(entityName);

  const fallbackMap = {
    crear: `No se pudo crear ${cleanEntity}. Verifique los datos e intente nuevamente.`,
    actualizar: `No se pudo actualizar ${cleanEntity}. Verifique los cambios e intente nuevamente.`,
    eliminar: `No se pudo eliminar ${cleanEntity}. Puede estar en uso en otros registros.`,
  };

  const backendMessage = getSafeErrorMessage(error, "");
  if (backendMessage) {
    const mapped = mapBackendMessage(backendMessage, action, entityName);
    return mapped ?? backendMessage;
  }

  return fallbackMap[action];
}

function CatalogPanel({
  def,
  canCreate,
  canEdit,
  canDelete,
}: {
  def: CatalogDef;
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
}) {
  const queryClient = useQueryClient();
  const nameField = def.nameField ?? "nombre";
  const isBibliographicAuthor = def.endpoint === "/autores/";
  const isAdoptante = def.endpoint === "/adoptantes";
  const nameLabel = isBibliographicAuthor ? "Nombre y apellido" : "Nombre";
  const validName = (value: string) => isBibliographicAuthor || isAdoptante
    ? hasOnlyLettersAndSpaces(value)
    : hasDescriptiveCatalogName(value);

  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<"create" | "update" | "delete" | null>(null);
  const actionInFlight = useRef(false);
  const [fkOptions, setFkOptions] = useState<CatalogItem[]>([]);
  const [historyByItem, setHistoryByItem] = useState<CatalogHistoryMap>({});
  const [openHistoryId, setOpenHistoryId] = useState<number | null>(null);
  const [historyLoadingId, setHistoryLoadingId] = useState<number | null>(null);
  const [historyErrorId, setHistoryErrorId] = useState<number | null>(null);
  const [historyPageByItem, setHistoryPageByItem] = useState<Record<number, number>>({});

  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newFkId, setNewFkId] = useState<number | "">("");

  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editFkId, setEditFkId] = useState<number | "">("");

  const [deleteTarget, setDeleteTarget] = useState<CatalogItem | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [currentPage, setCurrentPage] = useState(1);
  const [errorMessage, setErrorMessage] = useState("");
  const [toast, setToast] = useState<ToastState>({
    open: false,
    message: "",
    variant: "success",
  });

  const entityLabel = def.label.toLowerCase();
  const fkLabel = def.fkField?.label ?? "";
  const fkOptionLabel = def.fkField?.optionLabel ?? "nombre";

  const showToast = (message: string, variant: "success" | "error") => {
    setToast({ open: true, message, variant });
  };

  const load = async () => {
    setLoading(true);
    try {
      const data = await getCatalogItems(def.endpoint);
      setItems(data);
      setHistoryByItem({});
      setOpenHistoryId(null);
      setHistoryErrorId(null);
      setErrorMessage("");
    } catch {
      setErrorMessage(
        "Lo sentimos, no pudimos recuperar la información. Intente nuevamente."
      );
    } finally {
      setLoading(false);
    }
  };

  const toggleHistory = async (id: number, retry = false) => {
    if (openHistoryId === id && !retry) {
      setOpenHistoryId(null);
      return;
    }
    setOpenHistoryId(id);
    setHistoryPageByItem((current) => ({ ...current, [id]: 1 }));
    if (historyByItem[id] && !retry) return;
    setHistoryLoadingId(id);
    setHistoryErrorId(null);
    try {
      const history = await getCatalogHistory(def.endpoint, id);
      setHistoryByItem((current) => ({ ...current, [id]: history }));
    } catch {
      setHistoryErrorId(id);
    } finally {
      setHistoryLoadingId(null);
    }
  };

  useEffect(() => {
    if (def.fkField) {
      getCatalogItems(def.fkField.endpoint)
        .then(setFkOptions)
        .catch(() =>
          setErrorMessage(
            `Lo sentimos, no pudimos recuperar las opciones de ${fkLabel.toLowerCase()}. Intente nuevamente.`
          )
        );
    }
  }, [def.fkField]);

  useEffect(() => {
    load();
  }, [def.endpoint]);

  const getDisplayName = (item: CatalogItem) =>
    (item[nameField] as string) ?? item.nombre ?? "-";

  const getFkDisplayName = (item: CatalogItem): string | null => {
    if (!def.fkField) return null;
    const fk = item.fuente_financiamiento as { id: number; nombre: string } | null;
    return fk?.nombre ?? null;
  };

  const getFkId = (item: CatalogItem): number | "" => {
    if (!def.fkField) return "";
    const fk = item.fuente_financiamiento as { id: number } | null;
    return fk?.id ?? "";
  };

  const filteredItems = useMemo(
    () =>
      items.filter((item) => {
        const matchesSearch = normalizeText(getDisplayName(item)).includes(
          normalizeText(search)
        );
        const matchesStatus =
          statusFilter === "all" ||
          !hasStatusData(item) ||
          (statusFilter === "active" && !isInactive(item)) ||
          (statusFilter === "inactive" && isInactive(item));

        return matchesSearch && matchesStatus;
      }),
    [items, nameField, search, statusFilter]
  );

  const hasAnyStatusData = items.some(hasStatusData);
  const totalPages = Math.max(
    1,
    Math.ceil(filteredItems.length / CATALOG_ITEMS_PER_PAGE)
  );
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * CATALOG_ITEMS_PER_PAGE;
    return filteredItems.slice(start, start + CATALOG_ITEMS_PER_PAGE);
  }, [currentPage, filteredItems]);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, statusFilter]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const handleAdd = async () => {
    if (actionInFlight.current) return;
    if (!canCreate) return;
    if (!newName.trim()) {
      setErrorMessage("Debe ingresar un nombre antes de crear el registro.");
      return;
    }
    if (!validName(newName)) {
      setErrorMessage(isBibliographicAuthor || isAdoptante ? "Ingrese un nombre con letras y espacios." : "El nombre debe contener al menos una letra.");
      return;
    }

    if (def.fkField && !newFkId) {
      setErrorMessage(`Debe seleccionar ${fkLabel.toLowerCase()}.`);
      return;
    }

    const body: Record<string, unknown> = { [nameField]: isBibliographicAuthor || isAdoptante ? newName.trim().replace(/\s+/g, " ") : newName.trim() };
    if (def.descField && newDesc.trim()) body[def.descField] = newDesc.trim();
    if (def.fkField && newFkId) body[def.fkField.idField] = Number(newFkId);

    actionInFlight.current = true;
    setPendingAction("create");
    try {
      await createCatalogItem(def.endpoint, body);
      setNewName("");
      setNewDesc("");
      setNewFkId("");
      setShowAdd(false);
      setErrorMessage("");
      showToast(`El registro se creo correctamente en ${def.label}.`, "success");
      await queryClient.invalidateQueries();
      await load();
    } catch (error) {
      const message = getCatalogErrorMessage(
        error,
        "crear",
        `el registro de ${def.label}`
      );
      setErrorMessage(message);
      showToast(message, "error");
    } finally {
      actionInFlight.current = false;
      setPendingAction(null);
    }
  };

  const handleUpdate = async (id: number) => {
    if (actionInFlight.current) return;
    if (!canEdit) return;
    const item = items.find((current) => current.id === id);
    if (!item) {
      setErrorMessage("No se encontró el registro que desea actualizar.");
      return;
    }
    if (item && isInactive(item)) {
      const message = `No se puede editar el registro de ${def.label} porque está inactivo.`;
      setEditId(null);
      setErrorMessage(message);
      showToast(message, "error");
      return;
    }

    if (!editName.trim()) {
      setErrorMessage("El nombre no puede estar vacio.");
      return;
    }

    const body: Record<string, unknown> = {};
    const normalizedName = isBibliographicAuthor || isAdoptante ? editName.trim().replace(/\s+/g, " ") : editName.trim();
    if (normalizedName !== getDisplayName(item) && !validName(normalizedName)) {
      setErrorMessage(isBibliographicAuthor || isAdoptante ? "Ingrese un nombre con letras y espacios." : "El nombre debe contener al menos una letra.");
      return;
    }
    if (normalizedName !== getDisplayName(item)) body[nameField] = normalizedName;
    if (def.descField) {
      const currentDescription =
        typeof item?.[def.descField] === "string" ? item[def.descField] : "";
      if (editDesc.trim() !== currentDescription) body[def.descField] = editDesc.trim();
    }
    if (def.fkField) {
      const nextFkId = editFkId ? Number(editFkId) : null;
      const currentFkId = getFkId(item);
      if (nextFkId !== (currentFkId || null)) body[def.fkField.idField] = nextFkId;
    }

    if (Object.keys(body).length === 0) {
      setEditId(null);
      setErrorMessage("");
      showToast("No hubo cambios para actualizar.", "success");
      return;
    }

    actionInFlight.current = true;
    setPendingAction("update");
    try {
      await updateCatalogItem(def.endpoint, id, body);
      setEditId(null);
      setErrorMessage("");
      showToast(`Los cambios se guardaron correctamente en ${def.label}.`, "success");
      await queryClient.invalidateQueries();
      await load();
    } catch (error) {
      const message = getCatalogErrorMessage(
        error,
        "actualizar",
        `el registro de ${def.label}`
      );
      setErrorMessage(message);
      showToast(message, "error");
    } finally {
      actionInFlight.current = false;
      setPendingAction(null);
    }
  };

  const handleDelete = async () => {
    if (actionInFlight.current) return;
    if (!canDelete) return;
    if (!deleteTarget) return;
    if (isInactive(deleteTarget)) {
      const message = `No se puede eliminar el registro de ${def.label} porque ya está inactivo.`;
      setDeleteTarget(null);
      setErrorMessage(message);
      showToast(message, "error");
      return;
    }

    actionInFlight.current = true;
    setPendingAction("delete");
    try {
      await deleteCatalogItem(def.endpoint, deleteTarget.id);
      setDeleteTarget(null);
      setErrorMessage("");
      showToast(`El registro se elimino correctamente de ${def.label}.`, "success");
      await queryClient.invalidateQueries();
      await load();
    } catch (error) {
      const message = getCatalogErrorMessage(
        error,
        "eliminar",
        `el registro de ${def.label}`
      );
      setDeleteTarget(null);
      setErrorMessage(message);
      showToast(message, "error");
    } finally {
      actionInFlight.current = false;
      setPendingAction(null);
    }
  };

  return (
    <div className="space-y-4 pt-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative md:w-80">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Buscar valor"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="flex gap-2" role="group" aria-label="Estado de valores">
          {(["all", "active", "inactive"] as StatusFilter[]).map((filter) => (
            <button
              key={filter}
              type="button"
              disabled={filter !== "all" && !hasAnyStatusData}
              onClick={() => setStatusFilter(filter)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                statusFilter === filter
                  ? "border-sky-200 bg-sky-50 text-sky-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              } disabled:cursor-not-allowed disabled:opacity-40`}
            >
              {filter === "all" ? "Todos" : filter === "active" ? "Activos" : "Inactivos"}
            </button>
          ))}
        </div>
      </div>

      {loading && <LoadingSkeleton variant="table" label="Cargando catálogo…" />}
      {!!errorMessage && <ErrorText>{errorMessage}</ErrorText>}

      {!loading && items.length === 0 && (
        <p className="text-sm text-slate-400 italic">Sin registros</p>
      )}

      {!loading && items.length > 0 && filteredItems.length === 0 && (
        <p className="text-sm text-slate-400 italic">
          No hay valores que coincidan con la búsqueda o el filtro seleccionado.
        </p>
      )}

      {!loading && filteredItems.length > 0 && (
        <div className="space-y-3">
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Valores y acciones</div>

            <div className="divide-y divide-slate-100">
              {paginatedItems.map((item) => (
                <div
                  key={item.id}
                  className={`px-5 py-4 transition-colors ${
                editId === item.id
                  ? "bg-sky-50/50"
                  : "bg-white hover:bg-slate-50"
              }`}
            >
              {editId === item.id ? (
                <div className="space-y-3">
                  <Field
                    label={nameLabel}
                    required
                  >
                    <input
                      className="input"
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      onKeyDown={(event) => event.key === "Enter" && handleUpdate(item.id)}
                      autoFocus
                    />
                  </Field>

                  {def.descField && (
                    <Field label="Descripción">
                      <input
                        className="input"
                        value={editDesc}
                        placeholder="Descripción"
                        onChange={(event) => setEditDesc(event.target.value)}
                      />
                    </Field>
                  )}

                  {def.fkField && (
                    <Field label={fkLabel}>
                      <select
                        className="input"
                        value={editFkId}
                        onChange={(event) =>
                          setEditFkId(event.target.value ? +event.target.value : "")
                        }
                      >
                        <option value="">Sin {fkLabel.toLowerCase()}</option>
                        {fkOptions.map((option) => (
                          <option key={option.id} value={option.id}>
                            {String(option[fkOptionLabel] ?? option.nombre)}
                          </option>
                        ))}
                      </select>
                    </Field>
                  )}

                  <div className="flex justify-end gap-2 pt-1">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => setEditId(null)}
                    >
                      Cancelar
                    </Button>
                    <Button type="button" size="sm" onClick={() => handleUpdate(item.id)} loading={pendingAction === "update"} loadingText="Guardando..." disabled={pendingAction !== null}>
                      Guardar
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold text-slate-800">
                      {getDisplayName(item)}
                    </p>
                    {(def.descField && typeof item[def.descField] === "string") ||
                    getFkDisplayName(item) ? (
                      <p className="mt-0.5 truncate text-xs text-slate-400">
                        {def.descField && typeof item[def.descField] === "string" && (
                          <span>{item[def.descField] as string}</span>
                        )}
                        {def.descField &&
                          typeof item[def.descField] === "string" &&
                          getFkDisplayName(item) && <span> · </span>}
                        {getFkDisplayName(item) && (
                          <span>
                            {fkLabel}: {getFkDisplayName(item)}
                          </span>
                        )}
                      </p>
                    ) : null}

                  </div>

                  <div className="flex flex-wrap items-center gap-3 md:justify-end">
                    <div>
                      {hasStatusData(item) ? (
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider ${
                            isInactive(item)
                              ? "bg-rose-100 text-rose-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {isInactive(item) ? "Inactivo" : "Vigente"}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">
                          Estado no informado
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-slate-500">
                      {getAuditLabel(item, historyByItem[item.id] ?? [])}
                    </div>

                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      aria-expanded={openHistoryId === item.id}
                      onClick={() => void toggleHistory(item.id)}
                    >
                      <span className="flex items-center gap-1.5"><History size={14} aria-hidden="true" /> Historial</span>
                    </Button>

                    {canEdit && !isInactive(item) && (
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setEditId(item.id);
                          setEditName(getDisplayName(item));
                          setEditDesc(def.descField ? ((item[def.descField] as string) ?? "") : "");
                          setEditFkId(getFkId(item));
                          setErrorMessage("");
                        }}
                        title="Editar"
                      >
                        <span className="flex items-center gap-1.5">
                          <Pencil size={14} /> Editar
                        </span>
                      </Button>
                    )}

                    {canDelete && !isInactive(item) && (
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => setDeleteTarget(item)}
                        className="text-red-600 hover:bg-red-50"
                        title="Eliminar"
                      >
                        <span className="flex items-center gap-1.5">
                          <Trash2 size={14} /> Eliminar
                        </span>
                      </Button>
                    )}
                  </div>
                  {openHistoryId === item.id && (
                    <div className="rounded-lg bg-slate-50 px-3 py-3 md:col-span-2" role="region" aria-label={`Historial de ${getDisplayName(item)}`}>
                      {historyLoadingId === item.id ? (
                        <LoadingSkeleton variant="compact" label="Cargando historial…" />
                      ) : historyErrorId === item.id ? (
                        <div>
                          <ErrorText>Lo sentimos, no pudimos recuperar el historial. Intente nuevamente.</ErrorText>
                          <Button type="button" variant="secondary" size="sm" onClick={() => void toggleHistory(item.id, true)}>Reintentar</Button>
                        </div>
                      ) : (
                      <>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Historial de cambios
                      </p>
                      {(historyByItem[item.id] ?? []).length > 0 ? (
                        <>
                          <ul className="mt-2 space-y-1">
                          {(historyByItem[item.id] ?? [])
                            .slice(
                              ((historyPageByItem[item.id] ?? 1) - 1) *
                                HISTORY_ITEMS_PER_PAGE,
                              (historyPageByItem[item.id] ?? 1) *
                                HISTORY_ITEMS_PER_PAGE
                            )
                            .map((history) => (
                            <li key={history.id} className="text-xs text-slate-600">
                              {formatHistoryItem(history)}
                            </li>
                          ))}
                          </ul>
                          {(historyByItem[item.id] ?? []).length > HISTORY_ITEMS_PER_PAGE && (
                            <div className="mt-2 flex items-center gap-2">
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                disabled={(historyPageByItem[item.id] ?? 1) === 1}
                                onClick={() =>
                                  setHistoryPageByItem((current) => ({
                                    ...current,
                                    [item.id]: Math.max(1, (current[item.id] ?? 1) - 1),
                                  }))
                                }
                              >
                                Anterior
                              </Button>
                              <span className="text-xs text-slate-500">
                                Página {historyPageByItem[item.id] ?? 1} de{" "}
                                {Math.ceil(
                                  (historyByItem[item.id] ?? []).length /
                                    HISTORY_ITEMS_PER_PAGE
                                )}
                              </span>
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                disabled={
                                  (historyPageByItem[item.id] ?? 1) >=
                                  Math.ceil(
                                    (historyByItem[item.id] ?? []).length /
                                      HISTORY_ITEMS_PER_PAGE
                                  )
                                }
                                onClick={() =>
                                  setHistoryPageByItem((current) => ({
                                    ...current,
                                    [item.id]: Math.min(
                                      Math.ceil(
                                        (historyByItem[item.id] ?? []).length /
                                          HISTORY_ITEMS_PER_PAGE
                                      ),
                                      (current[item.id] ?? 1) + 1
                                    ),
                                  }))
                                }
                              >
                                Siguiente
                              </Button>
                            </div>
                          )}
                        </>
                      ) : (
                        <p className="mt-2 text-xs text-slate-400">
                          Sin cambios registrados para este valor.
                        </p>
                       )}
                      </>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
              ))}
            </div>
          </div>

          {totalPages > 1 && (
            <div className="mt-8">
              <nav aria-label="Paginación" className="flex flex-wrap items-center justify-center gap-1">
                <TableActionButton aria-label="Página anterior"
                  disabled={currentPage === 1} onClick={() => setCurrentPage((current) => current - 1)}>
                  Anterior
                </TableActionButton>
                {[...Array(totalPages)].map((_, index) => {
                  const pageNumber = index + 1;
                  return (
                    <button type="button" key={pageNumber} aria-label={`Página ${pageNumber}`}
                      aria-current={currentPage === pageNumber ? "page" : undefined}
                      onClick={() => setCurrentPage(pageNumber)}
                      className={`h-8 min-w-8 rounded-lg px-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-slate-500 ${
                        currentPage === pageNumber ? "bg-slate-800 text-white" : "hover:bg-slate-100"
                      }`}>
                      {pageNumber}
                    </button>
                  );
                })}
                <TableActionButton aria-label="Página siguiente"
                  disabled={currentPage === totalPages} onClick={() => setCurrentPage((current) => current + 1)}>
                  Siguiente
                </TableActionButton>
              </nav>
            </div>
          )}
        </div>
      )}

      {canCreate && (showAdd ? (
        <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50/30 px-4 py-4">
          <Field
            label={nameLabel}
            required
          >
            <input
              className="input"
              placeholder="Nombre"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handleAdd()}
              autoFocus
            />
          </Field>

          {def.descField && (
            <Field label="Descripción">
              <input
                className="input"
                placeholder="Descripción"
                value={newDesc}
                onChange={(event) => setNewDesc(event.target.value)}
              />
            </Field>
          )}

          {def.fkField && (
            <Field label={fkLabel} required>
              <select
                className="input"
                value={newFkId}
                onChange={(event) =>
                  setNewFkId(event.target.value ? +event.target.value : "")
                }
              >
                <option value="">Sin {fkLabel.toLowerCase()}</option>
                {fkOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {String(option[fkOptionLabel] ?? option.nombre)}
                  </option>
                ))}
              </select>
            </Field>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                setShowAdd(false);
                setNewName("");
                setNewDesc("");
                setNewFkId("");
                setErrorMessage("");
              }}
            >
              Cancelar
            </Button>
            <Button type="button" size="sm" onClick={handleAdd} loading={pendingAction === "create"} loadingText="Creando..." disabled={pendingAction !== null}>
              Crear
            </Button>
          </div>
        </div>
      ) : (
        <Button
          type="button"
          size="sm"
          onClick={() => {
            setShowAdd(true);
            setErrorMessage("");
          }}
        >
          <span className="flex items-center gap-2">
            <Plus size={16} /> Agregar nuevo
          </span>
        </Button>
      ))}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Eliminar registro"
        message={isBibliographicAuthor
          ? `Antes de eliminar "${deleteTarget ? getDisplayName(deleteTarget) : ""}", verifique que no esté vinculado a una documentación activa. Si tiene vinculaciones activas, el sistema bloqueará la baja.`
          : `Antes de eliminar "${deleteTarget ? getDisplayName(deleteTarget) : ""}", verifique que no esté asociado a registros históricos o memorias. Si está en uso, el sistema puede bloquear la operación.`}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        loading={pendingAction === "delete"}
       loadingText="Eliminando..."
     />

      <SuccessToast
        open={toast.open}
        message={toast.message}
        variant={toast.variant}
        onClose={() =>
          setToast({
            open: false,
            message: "",
            variant: "success",
          })
        }
      />
    </div>
  );
}

export default function CatalogosHome() {
  const navigate = useNavigate();
  const { canCreateRecords, canEditRecords, canDeleteRecords } = useAuth();
  const [selectedEndpoint, setSelectedEndpoint] = useState(CATALOGS[0].endpoint);
  const selectedCatalog = CATALOGS.find((catalog) => catalog.endpoint === selectedEndpoint) ?? CATALOGS[0];

  return (
    <section className="w-full min-h-[calc(100vh-120px)] px-4 py-4 flex flex-col">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold md:text-3xl">Gestionar Catálogos</h2>
          <p className="mt-1 text-sm text-slate-500">
            Consulte y administre las opciones que usan los formularios.
          </p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={() => navigate(-1)}>Volver</Button>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <Field label="Tipo de catálogo">
          <select className="input max-w-lg" value={selectedEndpoint} onChange={(event) => setSelectedEndpoint(event.target.value)}>
            {CATALOGS.map((catalog) => (
              <option key={catalog.endpoint} value={catalog.endpoint}>{catalog.label}</option>
            ))}
          </select>
        </Field>
        <p className="mt-3 text-sm text-slate-600">{selectedCatalog.description}</p>
        <CatalogPanel
          key={selectedCatalog.endpoint}
          def={selectedCatalog}
          canCreate={canCreateRecords()}
          canEdit={canEditRecords()}
          canDelete={canDeleteRecords()}
        />
      </div>
      <button type="button" className="mt-8 inline-flex items-center justify-center gap-2 self-center text-sm text-slate-600 hover:text-slate-900" onClick={scrollToPageTop}>
        <ArrowUp className="h-4 w-4" aria-hidden="true" /> Volver arriba
      </button>
    </section>
  );
}
