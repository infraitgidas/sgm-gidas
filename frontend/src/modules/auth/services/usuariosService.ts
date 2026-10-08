import { http } from "@/lib/http";
import type { Rol } from "./authService";

export type UsuarioRol = Rol;

export type Usuario = {
  id: number;
  nombre_usuario: string;
  mail: string;
  rol: UsuarioRol;
  activo: boolean;
  primer_login: boolean;
  fecha_creacion?: string;
  nombre?: string;
  persona?: {
    id: number;
    nombre: string;
  };
};

export type CrearUsuarioPayload = {
  nombre_usuario: string;
  mail: string;
  password: string;
  rol_id: number;
};

export type ActualizarUsuarioPayload = {
  nombre_usuario?: string;
  mail?: string;
  rol_id?: number;
  activo?: boolean;
};

type ActualizarUsuarioResponse = {
  mensaje: string;
  usuario: Usuario;
};
export function rolToRolId(rol: Rol): number {
  switch (rol) {
    case "ADMIN":
      return 1;
    case "GESTOR":
      return 2;
    case "LECTURA":
      return 3;
    default:
      return 2;
  }
}

export async function getUsuarios(): Promise<Usuario[]> {
  return http<Usuario[]>("/auth/usuarios", {
    method: "GET",
  });
}

export async function getUsuarioId(id: number): Promise<Usuario> {
  return http<Usuario>(`/auth/usuarios/${id}`, {
    method: "GET",
  });
}

export async function crearUsuario(payload: CrearUsuarioPayload): Promise<Usuario> {
  return http<Usuario>("/auth/usuarios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function actualizarUsuario(
  id: number,
  payload: ActualizarUsuarioPayload
): Promise<Usuario> {
  const response = await http<Usuario | ActualizarUsuarioResponse>(`/auth/usuarios/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

  return "usuario" in response ? response.usuario : response;
}

export async function eliminarUsuario(id: number): Promise<void> {
  await http(`/auth/usuarios/${id}`, {
    method: "DELETE",
  });
}
