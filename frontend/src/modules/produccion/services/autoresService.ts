import { http } from "@/lib/http";

export interface Autor {
  id: number;
  grupo_utn_id?: number | null;
  nombre_apellido: string;
}

// GET ALL
export async function getAutores(): Promise<Autor[]> {
  return http<Autor[]>("/autores/");
}

// CREATE
export async function createAutor(
  nombre_apellido: string
): Promise<Autor> {
  return http<Autor>("/autores/", {
    method: "POST",
    body: JSON.stringify({ nombre_apellido }),
  });
}

// UPDATE
export async function updateAutor(
  id: number,
  nombre_apellido: string
): Promise<Autor> {
  return http<Autor>(`/autores/${id}`, {
    method: "PUT",
    body: JSON.stringify({ nombre_apellido }),
  });
}

// DELETE
export async function deleteAutor(id: number): Promise<void> {
  return http<void>(`/autores/${id}`, {
    method: "DELETE",
  });
}
