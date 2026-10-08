import type { Autor } from "@/modules/produccion/services/documentacionServices";

export function normalizarNombreAutor(nombre: string) {
  return nombre.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es").trim().replace(/\s+/g, " ");
}

export function buscarAutoresDisponibles(options: Autor[], selected: Autor[], search: string) {
  const ids = new Set(selected.filter((autor) => autor.id > 0).map((autor) => autor.id));
  const names = new Set(selected.map((autor) => normalizarNombreAutor(autor.nombre_apellido)));
  const query = normalizarNombreAutor(search);
  const terms = query.split(" ").filter(Boolean);
  const initialsQuery = query.replace(/[.\s]/g, "");

  return options.filter((autor) => {
    const name = normalizarNombreAutor(autor.nombre_apellido);
    if (!name || ids.has(autor.id) || names.has(name)) return false;
    if (!query) return true;
    const initials = name.split(/[^a-z0-9]+/).filter(Boolean).map((part) => part[0]).join("");
    return terms.every((part) => name.includes(part)) || initials.startsWith(initialsQuery);
  });
}
