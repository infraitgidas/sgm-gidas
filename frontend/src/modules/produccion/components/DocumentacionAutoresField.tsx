import { useId, useState } from "react";
import Button from "@/components/Button";
import { hasOnlyLettersAndSpaces } from "@/lib/textValidation";
import type { Autor } from "@/modules/produccion/services/documentacionServices";
import { buscarAutoresDisponibles, normalizarNombreAutor } from "@/modules/produccion/utils/documentacionAutores";

type Props = {
  value: Autor[];
  options: Autor[];
  onChange: (autores: Autor[]) => void;
  disabled?: boolean;
};

export default function DocumentacionAutoresField({ value, options, onChange, disabled = false }: Props) {
  const id = useId();
  const [search, setSearch] = useState("");
  const [newName, setNewName] = useState("");
  const [newNameError, setNewNameError] = useState("");
  const [availablePage, setAvailablePage] = useState(1);
  const [selectedPage, setSelectedPage] = useState(1);
  const available = buscarAutoresDisponibles(options, value, search);
  const currentAvailablePage = Math.min(availablePage, Math.max(1, Math.ceil(available.length / 5)));
  const currentSelectedPage = Math.min(selectedPage, Math.max(1, Math.ceil(value.length / 5)));
  const availableStart = (currentAvailablePage - 1) * 5;
  const selectedStart = (currentSelectedPage - 1) * 5;

  const addNew = () => {
    if (disabled) return;
    const name = newName.trim().replace(/\s+/g, " ");
    if (!name || !hasOnlyLettersAndSpaces(name)) {
      setNewNameError("Ingrese un nombre con letras y espacios.");
      return;
    }
    if (value.some((autor) => normalizarNombreAutor(autor.nombre_apellido) === normalizarNombreAutor(name))) {
      setNewNameError("Este autor ya está seleccionado.");
      return;
    }
    if (options.some((autor) => normalizarNombreAutor(autor.nombre_apellido) === normalizarNombreAutor(name))) {
      setNewNameError("Este autor ya existe. Búsquelo y añádalo desde la lista.");
      return;
    }
    onChange([...value, { id: Math.min(0, ...value.map((autor) => autor.id)) - 1, nombre_apellido: name }]);
    setSelectedPage(Math.ceil((value.length + 1) / 5));
    setNewName("");
    setNewNameError("");
  };

  return <div className="space-y-3">
    <div>
      <label htmlFor={`${id}-search`} className="mb-1 block text-sm">Buscar autores</label>
      <input id={`${id}-search`} type="search" className="input w-full" value={search} disabled={disabled}
        placeholder="Nombre, apellido o iniciales" aria-describedby={`${id}-search-help`}
        onChange={(event) => { setSearch(event.target.value); setAvailablePage(1); }}
        onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }} />
    </div>
    <p id={`${id}-search-help`} className="text-xs text-slate-500">Busque un autor y pulse Añadir para incorporarlo al documento.</p>
    <p role="status" className="text-xs text-slate-500">
      {available.length ? `Mostrando ${availableStart + 1} a ${Math.min(availableStart + 5, available.length)} de ${available.length} autores disponibles.` :
        search ? "No hay coincidencias. Pruebe otro nombre o iniciales." : "No hay más autores disponibles para añadir."}
    </p>
    <ul aria-label="Resultados de autores" className="space-y-2">
      {available.slice(availableStart, availableStart + 5).map((autor) => <li key={autor.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm">
        <span className="min-w-0 break-words">{autor.nombre_apellido}</span>
        <Button type="button" variant="secondary" size="sm" disabled={disabled}
          aria-label={`Añadir a ${autor.nombre_apellido}`} onClick={() => { onChange([...value, autor]); setSelectedPage(Math.ceil((value.length + 1) / 5)); }}>Añadir</Button>
      </li>)}
    </ul>
    {available.length > 5 && <nav aria-label="Páginas de autores disponibles" className="flex items-center gap-2 text-sm">
      <Button type="button" variant="secondary" size="sm" disabled={disabled || currentAvailablePage === 1} onClick={() => setAvailablePage(currentAvailablePage - 1)}>Anterior</Button>
      <span role="status">Página {currentAvailablePage} de {Math.ceil(available.length / 5)}</span>
      <Button type="button" variant="secondary" size="sm" disabled={disabled || currentAvailablePage === Math.ceil(available.length / 5)} onClick={() => setAvailablePage(currentAvailablePage + 1)}>Siguiente</Button>
    </nav>}
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <label htmlFor={`${id}-new`} className="mb-1 block text-sm font-medium">Nuevo autor</label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input id={`${id}-new`} className="input w-full" value={newName} disabled={disabled}
          placeholder="Nombre y apellido" aria-invalid={Boolean(newNameError)} aria-describedby={newNameError ? `${id}-new-error` : undefined}
          onChange={(event) => { setNewName(event.target.value); setNewNameError(""); }}
          onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addNew(); } }} />
        <Button type="button" variant="secondary" size="sm" disabled={disabled} onClick={addNew}>Añadir</Button>
      </div>
      {newNameError && <p id={`${id}-new-error`} role="alert" className="mt-2 text-sm text-rose-700">{newNameError}</p>}
    </div>
    <p className="text-sm font-medium">Autores seleccionados ({value.length})</p>
    {value.length === 0 && <p className="text-sm text-slate-500">Todavía no añadió autores.</p>}
    <ul aria-label="Autores seleccionados" className="space-y-2">
      {value.slice(selectedStart, selectedStart + 5).map((autor) => <li key={autor.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm">
        <span className="min-w-0 break-words">{autor.nombre_apellido}{autor.id <= 0 && <span className="ml-1 text-xs text-slate-500">(nuevo)</span>}</span>
        <Button type="button" variant="secondary" size="sm" disabled={disabled} aria-label={`Quitar a ${autor.nombre_apellido}`}
          onClick={() => onChange(value.filter((item) => item.id !== autor.id))}>Quitar</Button>
      </li>)}
    </ul>
    {value.length > 5 && <nav aria-label="Páginas de autores seleccionados" className="flex items-center gap-2 text-sm">
      <Button type="button" variant="secondary" size="sm" disabled={disabled || currentSelectedPage === 1} onClick={() => setSelectedPage(currentSelectedPage - 1)}>Anterior</Button>
      <span role="status">Página {currentSelectedPage} de {Math.ceil(value.length / 5)}</span>
      <Button type="button" variant="secondary" size="sm" disabled={disabled || currentSelectedPage === Math.ceil(value.length / 5)} onClick={() => setSelectedPage(currentSelectedPage + 1)}>Siguiente</Button>
    </nav>}
    <p className="text-xs text-slate-500">Las altas y bajas de autores se aplicarán al guardar el documento.</p>
  </div>;
}
