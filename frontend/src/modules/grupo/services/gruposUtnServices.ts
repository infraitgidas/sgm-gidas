import {http} from "@/lib/http";

export interface GrupoUtn {
  id: number;
  nombre: string;
}

export const getGruposUtn = async (): Promise<GrupoUtn[]> => {
  return http<GrupoUtn[]>("/grupo-utn/opciones", {
    method: "GET",
  });
};
