import type { ParticipanteRef, ParticipanteRol } from "@/modules/proyectos/services/participacionesServices";

export type ParticipanteBuscable = ParticipanteRef & {
  nombre_apellido: string;
  tipo: "Investigador" | "Becario";
};

export const participanteClave = (participante: ParticipanteRef) =>
  `${participante.rol}:${participante.id}`;

export const normalizarBusquedaParticipante = (texto: string) =>
  texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("es")
    .trim();

export const filtrarParticipantes = (
  participantes: ParticipanteBuscable[],
  busqueda: string,
  categoria: ParticipanteRol | "",
  seleccionado?: ParticipanteRef | null
) => {
  const consulta = normalizarBusquedaParticipante(busqueda);
  const partes = consulta.split(/\s+/).filter(Boolean);
  const claveSeleccionada = seleccionado ? participanteClave(seleccionado) : null;

  return participantes.filter((participante) => {
    if (participanteClave(participante) === claveSeleccionada) return false;
    if (categoria && participante.rol !== categoria) return false;

    const nombre = normalizarBusquedaParticipante(participante.nombre_apellido);
    const iniciales = nombre
      .split(/[^a-z0-9]+/)
      .filter(Boolean)
      .map((parte) => parte[0])
      .join("");

    return (
      partes.every((parte) => nombre.includes(parte)) ||
      iniciales.startsWith(consulta.replace(/[.\s]/g, ""))
    );
  });
};
