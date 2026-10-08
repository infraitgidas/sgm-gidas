import { http } from "@/lib/http";

export type AutorRol = "investigador" | "becario";
export interface AutorReferencia { id: number; rol: AutorRol }
export interface IntegranteAutor extends AutorReferencia {
  nombre_apellido: string;
  tipo: string;
  activo: boolean;
}

export const esAutorSeleccionable = (autor: { rol: string; activo: boolean }) =>
  (autor.rol === "investigador" || autor.rol === "becario") && autor.activo === true;

export const autorClave = (autor: AutorReferencia) => `${autor.rol}:${autor.id}`;
export const autorEtiqueta = (autor: IntegranteAutor) => `${autor.nombre_apellido} (${autor.tipo})`;
export const mismasAutorias = (a: AutorReferencia[], b: AutorReferencia[]) =>
  a.length === b.length && a.every(autor => b.some(otro => autorClave(autor) === autorClave(otro)));

export async function getIntegrantesAutores(): Promise<IntegranteAutor[]> {
  const integrantes = await http<Array<{
    id: number; rol: string; nombre_apellido: string; activo: boolean;
  }>>("/personal-all?activos=true");
  return integrantes.filter((persona): persona is typeof persona & { rol: AutorRol } =>
    esAutorSeleccionable(persona)
  ).map(persona => ({
    id: persona.id, rol: persona.rol, nombre_apellido: persona.nombre_apellido,
    activo: persona.activo,
    tipo: persona.rol === "investigador" ? "Investigador" : "Becario",
  }));
}
