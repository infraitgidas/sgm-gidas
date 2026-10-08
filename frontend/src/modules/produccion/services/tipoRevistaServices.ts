import { http } from "@/lib/http";

export interface TipoRevista {
  id: number;
  nombre: string;
}

export const getTiposRevista = async (): Promise<TipoRevista[]> =>
  http("/tipos-revista/", { method: "GET" });
