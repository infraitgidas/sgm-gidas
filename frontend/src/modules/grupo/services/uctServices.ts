import { http, httpDownload } from "@/lib/http";
import { getErrorMessage } from "@/lib/httpError";

export type Uct = {
  id: number;
  facultadRegional: string;
  nombreSigla: string;
  director: string;
  vicedirector: string;
  correo: string;
  objetivos: string;

  directivos?: {
    id: number;
    nombre_apellido: string;
    cargo: string;
    fecha_inicio: string;
  }[];
};

export type HistorialGrupoItem = {
  id: number;
  campo: string;
  valor_anterior: string | null;
  valor_nuevo: string | null;
  fecha_cambio: string;
  usuario_nombre: string | null;
};

type UctApiResponse = {
  id: number;
  nombre_unidad_academica: string;
  nombre_sigla_grupo: string;
  mail: string;
  objetivo_desarrollo: string;
  director: string;
  vicedirector: string;
  directivos?: Uct["directivos"];
};

const BASE = import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL;

export async function getUct() {
  if (!BASE) return null;

  try {
    const data = await http<UctApiResponse>("/grupo-utn/");

    if (!data) return null;

    return {
      id: data.id,
      facultadRegional: data.nombre_unidad_academica,
      nombreSigla: data.nombre_sigla_grupo,
      correo: data.mail,
      objetivos: data.objetivo_desarrollo,
      director: data.director,
      vicedirector: data.vicedirector,
      directivos: data.directivos ?? [],
    };
  } catch {
    return null;
  }
}

export function getHistorialGrupo(grupoId: number) {
  return http<HistorialGrupoItem[]>(`/grupo-utn/${grupoId}/historial`);
}

export async function upsertUct(payload: Partial<Uct>, exists: boolean) {
  if (!BASE) return;

  const body = Object.fromEntries(
    [
      ["nombre_unidad_academica", payload.facultadRegional],
      ["nombre_sigla_grupo", payload.nombreSigla],
      ["mail", payload.correo],
      ["objetivo_desarrollo", payload.objetivos],
      ["director", payload.director],
      ["vicedirector", payload.vicedirector],
    ].filter(([, value]) => value !== undefined)
  );

  const method = exists ? "PUT" : "POST";

  return http("/grupo-utn/", { method, body: JSON.stringify(body) });
}

export async function deleteUct() {
  return http<void>("/grupo-utn/", {
    method: "DELETE",
  });
}

function getFilenameFromDisposition(contentDisposition: string | null): string {
  if (!contentDisposition) return "grupo_utn.xlsx";

  const utf8Match = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].replace(/["']/g, ""));
  }

  const quotedMatch = contentDisposition.match(/filename\s*=\s*"([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const plainMatch = contentDisposition.match(/filename\s*=\s*([^;]+)/i);
  if (plainMatch?.[1]) {
    return plainMatch[1].replace(/["']/g, "").trim();
  }

  return "grupo_utn.xlsx";
}

export async function exportarExcelGrupo(): Promise<{
  filename: string;
  size: number;
}> {
  try {
    const response = await httpDownload("/grupo-utn/exportar-excel", {
      method: "GET",
    });

    const blob = await response.blob();

    if (!blob || blob.size === 0) {
      throw new Error("El archivo exportado está vacío.");
    }

    const contentType = response.headers.get("content-type") || "";
    const allowedTypes = [
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/octet-stream",
    ];

    const isValidType =
      !contentType ||
      allowedTypes.some((type) => contentType.includes(type));

    if (!isValidType) {
      throw new Error(
        "La respuesta del servidor no corresponde a un archivo Excel válido."
      );
    }

    const filename = getFilenameFromDisposition(
      response.headers.get("content-disposition")
    );

    const url = window.URL.createObjectURL(blob);

    try {
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } finally {
      window.URL.revokeObjectURL(url);
    }

    return {
      filename,
      size: blob.size,
    };
  } catch (error) {
    throw new Error(
      getErrorMessage(
        error,
        "Lo sentimos, no pudimos exportar el archivo. Intente nuevamente."
      )
    );
  }
}
