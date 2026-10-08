import { useId, useState } from "react";

import Button from "@/components/Button";
import type { ParticipanteRol } from "@/modules/proyectos/services/participacionesServices";
import {
  filtrarParticipantes,
  participanteClave,
  type ParticipanteBuscable,
} from "@/modules/proyectos/utils/participanteSearch";

type Props = {
  value: ParticipanteBuscable | null;
  options: ParticipanteBuscable[];
  onChange: (participante: ParticipanteBuscable | null) => void;
  disabled?: boolean;
};

const RESULTADOS_POR_PAGINA = 5;

export default function ParticipanteField({ value, options, onChange, disabled }: Props) {
  const id = useId();
  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState<ParticipanteRol | "">("");
  const [pagina, setPagina] = useState(1);
  const resultados = filtrarParticipantes(options, busqueda, categoria, value);
  const totalPaginas = Math.max(1, Math.ceil(resultados.length / RESULTADOS_POR_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const inicio = (paginaActual - 1) * RESULTADOS_POR_PAGINA;

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor={`${id}-buscar`} className="mb-1 block text-sm">Buscar participante</label>
          <input
            id={`${id}-buscar`}
            type="search"
            className="input w-full"
            value={busqueda}
            disabled={disabled}
            placeholder="Nombre, apellido o iniciales"
            aria-describedby={`${id}-ayuda`}
            onChange={(event) => {
              setBusqueda(event.target.value);
              setPagina(1);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") event.preventDefault();
            }}
          />
        </div>
        <div>
          <label htmlFor={`${id}-categoria`} className="mb-1 block text-sm">Categoría</label>
          <select
            id={`${id}-categoria`}
            className="input w-full"
            value={categoria}
            disabled={disabled}
            onChange={(event) => {
              setCategoria(event.target.value as ParticipanteRol | "");
              setPagina(1);
            }}
          >
            <option value="">Investigadores y becarios</option>
            <option value="investigador">Investigadores</option>
            <option value="becario">Becarios</option>
          </select>
        </div>
      </div>

      <p id={`${id}-ayuda`} className="text-xs text-slate-500">
        Busque una persona y pulse Seleccionar para asignarla a la participación.
      </p>
      <p role="status" className="text-xs text-slate-500">
        {resultados.length
          ? `Mostrando ${inicio + 1} a ${Math.min(inicio + RESULTADOS_POR_PAGINA, resultados.length)} de ${resultados.length} participantes disponibles.`
          : options.length > (value ? 1 : 0)
            ? "No hay coincidencias. Pruebe otro nombre o categoría."
            : "No hay más participantes disponibles para seleccionar."}
      </p>

      <ul aria-label="Resultados de participantes" className="space-y-2">
        {resultados.slice(inicio, inicio + RESULTADOS_POR_PAGINA).map((participante) => (
          <li
            key={participanteClave(participante)}
            className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm"
          >
            <span className="min-w-0 break-words">
              {participante.nombre_apellido} ({participante.tipo})
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={disabled}
              aria-label={`Seleccionar a ${participante.nombre_apellido} (${participante.tipo})`}
              onClick={() => {
                if (!disabled) onChange(participante);
              }}
            >
              Seleccionar
            </Button>
          </li>
        ))}
      </ul>

      {totalPaginas > 1 && (
        <nav aria-label="Páginas de participantes" className="flex items-center gap-2">
          <Button type="button" variant="secondary" size="sm" disabled={disabled || paginaActual === 1} onClick={() => setPagina(paginaActual - 1)}>Anterior</Button>
          <span className="text-sm" role="status">Página {paginaActual} de {totalPaginas}</span>
          <Button type="button" variant="secondary" size="sm" disabled={disabled || paginaActual === totalPaginas} onClick={() => setPagina(paginaActual + 1)}>Siguiente</Button>
        </nav>
      )}

      <p className="text-sm font-medium">Participante seleccionado</p>
      {!value && <p className="text-sm text-slate-500">Todavía no seleccionó un participante.</p>}
      {value && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 text-sm">
          <span className="min-w-0 break-words">
            {value.nombre_apellido} ({value.tipo})
          </span>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={disabled}
            aria-label={`Quitar a ${value.nombre_apellido}`}
            onClick={() => onChange(null)}
          >
            Quitar
          </Button>
        </div>
      )}
      <p className="text-xs text-slate-500">La selección se aplicará al guardar la participación.</p>
    </div>
  );
}
