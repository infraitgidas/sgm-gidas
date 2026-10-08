import { useId, useState } from "react";

import Button from "@/components/Button";

export type PersonaOption = {
  id: number;
  nombre_apellido: string;
};

type Props = {
  value: number[];
  options: PersonaOption[];
  onChange: (ids: number[]) => void;
  label?: string;
  isEdit?: boolean;
  onRemoveConfirm?: (personaId: number) => void;
  disabled?: boolean;
};

const PAGE_SIZE = 5;
const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es").trim();

export default function PersonalProyectoField({
  value,
  options,
  onChange,
  label,
  isEdit = false,
  onRemoveConfirm,
  disabled = false,
}: Props) {
  const id = useId();
  const [search, setSearch] = useState("");
  const [availablePage, setAvailablePage] = useState(1);
  const [selectedPage, setSelectedPage] = useState(1);
  const selectedIds = new Set(value.filter(Boolean));
  const available = options.filter((option) => !selectedIds.has(option.id) && normalize(option.nombre_apellido).includes(normalize(search)));
  const currentAvailablePage = Math.min(availablePage, Math.max(1, Math.ceil(available.length / PAGE_SIZE)));
  const currentSelectedPage = Math.min(selectedPage, Math.max(1, Math.ceil(value.length / PAGE_SIZE)));
  const availableStart = (currentAvailablePage - 1) * PAGE_SIZE;
  const selectedStart = (currentSelectedPage - 1) * PAGE_SIZE;
  const itemLabel = label ?? "integrantes";

  const addPerson = (personId: number) => {
    if (disabled) return;
    const emptyIndex = value.indexOf(0);
    if (emptyIndex >= 0) {
      const next = [...value];
      next[emptyIndex] = personId;
      onChange(next);
      setSelectedPage(Math.floor(emptyIndex / PAGE_SIZE) + 1);
    } else {
      onChange([...value, personId]);
      setSelectedPage(Math.ceil((value.length + 1) / PAGE_SIZE));
    }
  };

  const removePerson = (personId: number, index: number) => {
    if (disabled) return;
    if (isEdit && onRemoveConfirm && personId) {
      onRemoveConfirm(personId);
      return;
    }
    onChange(value.filter((_, currentIndex) => currentIndex !== index));
  };

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor={`${id}-search`} className="mb-1 block text-sm">Buscar {itemLabel}</label>
        <input
          id={`${id}-search`}
          type="search"
          className="input w-full"
          value={search}
          placeholder="Nombre o apellido"
          disabled={disabled}
          aria-describedby={`${id}-help`}
          onChange={(event) => { setSearch(event.target.value); setAvailablePage(1); }}
          onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }}
        />
      </div>
      <p id={`${id}-help`} className="text-xs text-slate-500">Busque una persona y pulse Añadir para incorporarla al proyecto.</p>
      <p role="status" className="text-xs text-slate-500">
        {available.length
          ? `Mostrando ${availableStart + 1} a ${Math.min(availableStart + PAGE_SIZE, available.length)} de ${available.length} ${itemLabel} disponibles.`
          : options.length > selectedIds.size
            ? "No hay coincidencias. Pruebe otro nombre o apellido."
            : `No hay más ${itemLabel} disponibles para añadir.`}
      </p>
      <ul aria-label={`${itemLabel} disponibles`} className="space-y-2">
        {available.slice(availableStart, availableStart + PAGE_SIZE).map((option) => (
          <li key={option.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm">
            <span className="min-w-0 break-words">{option.nombre_apellido}</span>
            <Button type="button" variant="secondary" size="sm" disabled={disabled} aria-label={`Añadir a ${option.nombre_apellido}`} onClick={() => addPerson(option.id)}>Añadir</Button>
          </li>
        ))}
      </ul>
      {available.length > PAGE_SIZE && <nav aria-label={`Páginas de ${itemLabel} disponibles`} className="flex items-center gap-2 text-sm">
        <Button type="button" variant="secondary" size="sm" disabled={currentAvailablePage === 1} onClick={() => setAvailablePage(currentAvailablePage - 1)}>Anterior</Button>
        <span role="status">Página {currentAvailablePage} de {Math.ceil(available.length / PAGE_SIZE)}</span>
        <Button type="button" variant="secondary" size="sm" disabled={currentAvailablePage === Math.ceil(available.length / PAGE_SIZE)} onClick={() => setAvailablePage(currentAvailablePage + 1)}>Siguiente</Button>
      </nav>}

      <p className="text-sm font-medium">{itemLabel[0].toLocaleUpperCase("es") + itemLabel.slice(1)} seleccionados ({value.length})</p>
      {value.length === 0 && <p className="text-sm text-slate-500">Todavía no añadió {itemLabel}.</p>}
      <ul aria-label={`${itemLabel} seleccionados`} className="space-y-2">
        {value.slice(selectedStart, selectedStart + PAGE_SIZE).map((personId, offset) => {
          const index = selectedStart + offset;
          const name = options.find((option) => option.id === personId)?.nombre_apellido ?? (personId ? `Integrante ${personId}` : "Selección pendiente");
          return <li key={`${personId}-${index}`} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm">
            <span className="min-w-0 break-words">{name}</span>
            <Button type="button" variant="secondary" size="sm" disabled={disabled} aria-label={`Quitar a ${name}`} onClick={() => removePerson(personId, index)}>Quitar</Button>
          </li>;
        })}
      </ul>
      {value.length > PAGE_SIZE && <nav aria-label={`Páginas de ${itemLabel} seleccionados`} className="flex items-center gap-2 text-sm">
        <Button type="button" variant="secondary" size="sm" disabled={currentSelectedPage === 1} onClick={() => setSelectedPage(currentSelectedPage - 1)}>Anterior</Button>
        <span role="status">Página {currentSelectedPage} de {Math.ceil(value.length / PAGE_SIZE)}</span>
        <Button type="button" variant="secondary" size="sm" disabled={currentSelectedPage === Math.ceil(value.length / PAGE_SIZE)} onClick={() => setSelectedPage(currentSelectedPage + 1)}>Siguiente</Button>
      </nav>}
      <p className="text-xs text-slate-500">Las altas y bajas se aplicarán al guardar el proyecto.</p>
    </div>
  );
}
