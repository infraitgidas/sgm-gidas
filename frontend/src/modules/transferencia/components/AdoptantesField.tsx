import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useMemo, useState } from "react";
import Button from "@/components/Button";
import { hasOnlyLettersAndSpaces } from "@/lib/textValidation";
import { useAdoptantes } from "@/modules/transferencia/hooks/useAdoptantes";
import type { Adoptante } from "@/modules/transferencia/services/adoptantesServices";

type Props = { selected: Adoptante[]; onChange: (items: Adoptante[]) => void; disabled?: boolean };

export default function AdoptantesField({ selected, onChange, disabled = false }: Props) {
  const query = useAdoptantes();
  const [search, setSearch] = useState("");
  const [availablePage, setAvailablePage] = useState(1);
  const [selectedPage, setSelectedPage] = useState(1);
  const [nombre, setNombre] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const options = useMemo(() => query.list.filter(item => !selected.some(value => value.id === item.id) && item.nombre.toLocaleLowerCase("es").includes(search.trim().toLocaleLowerCase("es"))), [query.list, selected, search]);
  const currentAvailablePage = Math.min(availablePage, Math.max(1, Math.ceil(options.length / 5)));
  const currentSelectedPage = Math.min(selectedPage, Math.max(1, Math.ceil(selected.length / 5)));
  const availableStart = (currentAvailablePage - 1) * 5;
  const selectedStart = (currentSelectedPage - 1) * 5;

  const addNew = () => {
    const clean = nombre.trim();
    if (!clean || !hasOnlyLettersAndSpaces(clean)) { setFieldErrors({ nombre: "Ingrese un nombre con letras y espacios." }); return; }
    if ([...query.list, ...selected].some(item => item.nombre.toLocaleLowerCase("es") === clean.toLocaleLowerCase("es"))) { setFieldErrors({ nombre: "Este adoptante ya existe. Selecciónelo desde la grilla." }); return; }
    const nextId = Math.min(0, ...selected.map(item => item.id)) - 1;
    onChange([...selected, { id: nextId, nombre: clean }]);
    setSelectedPage(Math.ceil((selected.length + 1) / 5));
    setNombre(""); setFieldErrors({}); setShowNew(false);
  };

  return <div className="space-y-3">
    <div><h3 className="text-base font-semibold">Adoptantes</h3><p className="text-sm text-slate-500">Agregue o quite adoptantes. Las vinculaciones se guardarán con la transferencia.</p></div>
    {query.isLoading && <LoadingSkeleton variant="compact" label="Cargando adoptantes…" />}
    {query.isError && <p role="alert" className="text-sm text-rose-700">Lo sentimos, no pudimos recuperar los adoptantes. <button type="button" className="underline" onClick={() => query.refetch()}>Reintentar</button></p>}
    {(!query.isError || query.list.length > 0) && <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input type="search" aria-label="Buscar adoptantes disponibles" className="input flex-1" placeholder="Buscar adoptante" value={search} onChange={event => { setSearch(event.target.value); setAvailablePage(1); }} onKeyDown={event => { if (event.key === "Enter") event.preventDefault(); }} disabled={disabled} />
        <Button type="button" variant="secondary" size="sm" onClick={() => setShowNew(value => !value)} disabled={disabled}>Nuevo adoptante</Button>
      </div>
      <p role="status" className="text-xs text-slate-500">{options.length ? `Mostrando ${availableStart + 1} a ${Math.min(availableStart + 5, options.length)} de ${options.length} adoptantes disponibles.` : "No hay adoptantes disponibles. Pruebe otro nombre o cree uno nuevo."}</p>
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-sm"><caption className="sr-only">Adoptantes disponibles</caption><thead className="bg-slate-50 text-slate-600"><tr><th scope="col" className="px-4 py-2">Adoptante</th><th scope="col" className="px-4 py-2 text-right">Acciones</th></tr></thead><tbody>
          {options.slice(availableStart, availableStart + 5).map(item => <tr key={item.id} className="border-t border-slate-200"><td className="px-4 py-2">{item.nombre}</td><td className="px-4 py-2 text-right"><Button type="button" variant="secondary" size="sm" aria-label={`Añadir a ${item.nombre}`} disabled={disabled} onClick={() => { onChange([...selected, item]); setSelectedPage(Math.ceil((selected.length + 1) / 5)); }}>Añadir</Button></td></tr>)}
          {!options.length && <tr><td colSpan={2} className="px-4 py-4 text-center text-slate-500">Sin resultados.</td></tr>}
        </tbody></table>
      </div>
      {options.length > 5 && <nav aria-label="Páginas de adoptantes disponibles" className="flex items-center gap-2 text-sm">
        <Button type="button" variant="secondary" size="sm" disabled={disabled || currentAvailablePage === 1} onClick={() => setAvailablePage(currentAvailablePage - 1)}>Anterior</Button>
        <span role="status">Página {currentAvailablePage} de {Math.ceil(options.length / 5)}</span>
        <Button type="button" variant="secondary" size="sm" disabled={disabled || currentAvailablePage === Math.ceil(options.length / 5)} onClick={() => setAvailablePage(currentAvailablePage + 1)}>Siguiente</Button>
      </nav>}
    </div>}
    {showNew && <div className="rounded-lg border border-slate-200 bg-slate-50 p-4"><label htmlFor="adoptante-nombre" className="block text-sm font-medium">Nombre del adoptante *</label><input id="adoptante-nombre" data-error-field="nombre" className="input mt-1" value={nombre} onChange={event => { setNombre(event.target.value); setFieldErrors({}); }} onKeyDown={event => { if (event.key === "Enter" && !event.nativeEvent.isComposing) { event.preventDefault(); addNew(); } }} placeholder="Ej: Municipalidad de Resistencia" aria-invalid={Boolean(fieldErrors.nombre)} aria-describedby={fieldErrors.nombre ? "adoptante-nombre-error" : undefined} disabled={disabled} />{fieldErrors.nombre && <p id="adoptante-nombre-error" role="alert" className="text-sm text-rose-700">{fieldErrors.nombre}</p>}<div className="mt-3 flex gap-2"><Button type="button" size="sm" onClick={addNew} disabled={disabled}>Añadir al formulario</Button><Button type="button" size="sm" variant="secondary" onClick={() => { setShowNew(false); setNombre(""); }}>Cancelar</Button></div><p className="mt-2 text-xs text-slate-500">El adoptante se creará al guardar la transferencia.</p></div>}
    <p className="text-sm font-medium">Adoptantes seleccionados ({selected.length})</p>
    <div className="overflow-x-auto rounded-lg border border-slate-200"><table className="w-full text-left text-sm"><caption className="sr-only">Adoptantes seleccionados</caption><thead className="bg-slate-50 text-slate-600"><tr><th scope="col" className="px-4 py-2">Adoptante</th><th scope="col" className="px-4 py-2 text-right">Acciones</th></tr></thead><tbody>{selected.length ? selected.slice(selectedStart, selectedStart + 5).map(item => <tr key={item.id} className="border-t border-slate-200"><td className="px-4 py-2">{item.nombre}{item.id < 0 && <span className="ml-2 text-xs text-slate-500">(nuevo, pendiente de guardar)</span>}</td><td className="px-4 py-2 text-right"><Button type="button" variant="secondary" size="sm" disabled={disabled} aria-label={`Quitar ${item.nombre}`} onClick={() => onChange(selected.filter(value => value.id !== item.id))}>Quitar</Button></td></tr>) : <tr><td colSpan={2} className="px-4 py-4 text-center text-slate-500">No hay adoptantes seleccionados.</td></tr>}</tbody></table></div>
    {selected.length > 5 && <nav aria-label="Páginas de adoptantes seleccionados" className="flex items-center gap-2 text-sm">
      <Button type="button" variant="secondary" size="sm" disabled={disabled || currentSelectedPage === 1} onClick={() => setSelectedPage(currentSelectedPage - 1)}>Anterior</Button>
      <span role="status">Página {currentSelectedPage} de {Math.ceil(selected.length / 5)}</span>
      <Button type="button" variant="secondary" size="sm" disabled={disabled || currentSelectedPage === Math.ceil(selected.length / 5)} onClick={() => setSelectedPage(currentSelectedPage + 1)}>Siguiente</Button>
    </nav>}
  </div>;
}
