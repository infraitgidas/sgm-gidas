import { useId, useState } from "react";
import Button from "@/components/Button";
import { autorClave, autorEtiqueta, esAutorSeleccionable, type IntegranteAutor } from "@/modules/produccion/services/trabajoAutoresServices";

type Props = {
  value: IntegranteAutor[];
  options: IntegranteAutor[];
  onChange: (autores: IntegranteAutor[]) => void;
  disabled?: boolean;
};

export default function IntegrantesAutoresField({ value, options, onChange, disabled }: Props) {
  const id = useId();
  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState("");
  const [paginaDisponibles, setPaginaDisponibles] = useState(1);
  const [paginaSeleccionados, setPaginaSeleccionados] = useState(1);
  const normalizar = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  const consulta = normalizar(busqueda);
  const seleccionados = new Set(value.map(autorClave));
  const disponibles = options.filter(autor => esAutorSeleccionable(autor) &&
    !seleccionados.has(autorClave(autor)));
  const resultados = disponibles.filter(autor => {
    if (categoria && autor.rol !== categoria) return false;
    const nombre = normalizar(autor.nombre_apellido);
    const iniciales = nombre.split(/[^a-z0-9]+/).filter(Boolean).map(parte => parte[0]).join("");
    return consulta.split(/\s+/).every(parte => nombre.includes(parte)) ||
      iniciales.startsWith(consulta.replace(/[.\s]/g, ""));
  });
  const paginaDisponible = Math.min(paginaDisponibles, Math.max(1, Math.ceil(resultados.length / 5)));
  const paginaSeleccionada = Math.min(paginaSeleccionados, Math.max(1, Math.ceil(value.length / 5)));
  const inicioDisponibles = (paginaDisponible - 1) * 5;
  const inicioSeleccionados = (paginaSeleccionada - 1) * 5;
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor={`${id}-buscar`} className="mb-1 block text-sm">Buscar autores</label>
          <input id={`${id}-buscar`} type="search" className="input w-full" value={busqueda} disabled={disabled}
            placeholder="Nombre, apellido o iniciales" aria-describedby={`${id}-ayuda`}
            onChange={event => { setBusqueda(event.target.value); setPaginaDisponibles(1); }}
            onKeyDown={event => { if (event.key === "Enter") event.preventDefault(); }} />
        </div>
        <div>
          <label htmlFor={`${id}-categoria`} className="mb-1 block text-sm">Categoría</label>
          <select id={`${id}-categoria`} className="input w-full" value={categoria} disabled={disabled}
            onChange={event => { setCategoria(event.target.value); setPaginaDisponibles(1); }}>
            <option value="">Investigadores y becarios</option>
            <option value="investigador">Investigadores</option>
            <option value="becario">Becarios</option>
          </select>
        </div>
      </div>
      <p id={`${id}-ayuda`} className="text-xs text-slate-500">Busque un integrante y pulse Añadir para incorporarlo al trabajo.</p>
      <p role="status" className="text-xs text-slate-500">
        {resultados.length ? `Mostrando ${inicioDisponibles + 1} a ${Math.min(inicioDisponibles + 5, resultados.length)} de ${resultados.length} autores disponibles.` :
          disponibles.length ? "No hay coincidencias. Pruebe otro nombre o categoría." : "No hay más autores disponibles para añadir."}
      </p>
      <ul aria-label="Resultados de autores" className="space-y-2">
        {resultados.slice(inicioDisponibles, inicioDisponibles + 5).map(autor => (
          <li key={autorClave(autor)} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm">
            <span className="min-w-0 break-words">{autorEtiqueta(autor)}</span>
            <Button type="button" variant="secondary" size="sm" disabled={disabled}
              aria-label={`Añadir a ${autor.nombre_apellido} (${autor.tipo})`}
              onClick={() => { if (!disabled) { onChange([...value, autor]); setPaginaSeleccionados(Math.ceil((value.length + 1) / 5)); } }}>Añadir</Button>
          </li>
        ))}
      </ul>
      {resultados.length > 5 && <nav aria-label="Páginas de autores disponibles" className="flex items-center gap-2 text-sm">
        <Button type="button" variant="secondary" size="sm" disabled={disabled || paginaDisponible === 1} onClick={() => setPaginaDisponibles(paginaDisponible - 1)}>Anterior</Button>
        <span role="status">Página {paginaDisponible} de {Math.ceil(resultados.length / 5)}</span>
        <Button type="button" variant="secondary" size="sm" disabled={disabled || paginaDisponible === Math.ceil(resultados.length / 5)} onClick={() => setPaginaDisponibles(paginaDisponible + 1)}>Siguiente</Button>
      </nav>}
      <p className="text-sm font-medium">Autores seleccionados ({value.length})</p>
      {value.length === 0 && <p className="text-sm text-slate-500">Todavía no añadió autores.</p>}
      <ul aria-label="Autores seleccionados" className="space-y-2">
        {value.slice(inicioSeleccionados, inicioSeleccionados + 5).map(autor => (
          <li key={autorClave(autor)} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm">
            <span className="min-w-0 break-words">{autorEtiqueta(autor)}{!autor.activo && " — Inactivo"}</span>
            <Button type="button" variant="secondary" size="sm" disabled={disabled}
              aria-label={`Quitar a ${autor.nombre_apellido}`} onClick={() => onChange(value.filter(item => autorClave(item) !== autorClave(autor)))}>
              Quitar
            </Button>
          </li>
        ))}
      </ul>
      {value.length > 5 && <nav aria-label="Páginas de autores seleccionados" className="flex items-center gap-2 text-sm">
        <Button type="button" variant="secondary" size="sm" disabled={disabled || paginaSeleccionada === 1} onClick={() => setPaginaSeleccionados(paginaSeleccionada - 1)}>Anterior</Button>
        <span role="status">Página {paginaSeleccionada} de {Math.ceil(value.length / 5)}</span>
        <Button type="button" variant="secondary" size="sm" disabled={disabled || paginaSeleccionada === Math.ceil(value.length / 5)} onClick={() => setPaginaSeleccionados(paginaSeleccionada + 1)}>Siguiente</Button>
      </nav>}
      <p className="text-xs text-slate-500">Las altas y bajas de autores se aplicarán al guardar el trabajo.</p>
    </div>
  );
}
