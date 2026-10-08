import { http } from "@/lib/http";

/* ───────────────────────────────────────────
   Tipos que devuelve el BACKEND
   GET /search?q=...&orden=...&eliminados=...
   ─────────────────────────────────────────── */

export type Orden = "alf_asc" | "alf_desc" | "fecha_asc" | "fecha_desc";
export type EstadoBusqueda = "activos" | "eliminados" | "all";
export const SEARCH_MAX_QUERY_LENGTH = 80;

/** Cada resultado que devuelve la API */
export type BackendResult = {
  tipo: string;
  id: number;
  titulo: string;
  subtitulo?: string | null;
  fecha?: string | null;
  url: string;
  extra?: Record<string, unknown>;
  activo?: boolean;
};

/** Wrapper de la respuesta completa */
type SearchResponse = {
  query: string;
  orden: Orden;
  total_resultados: number;
  resultados: BackendResult[];
  meta: SearchMeta;
};

export type SearchMeta = {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

export type SearchPageResult = {
  results: SearchResult[];
  meta: SearchMeta;
};

/* ───────────────────────────────────────────
   Tipo normalizado que usa la UI
   ─────────────────────────────────────────── */
export type SearchResult = {
  id: number;
  tipo: string;
  titulo: string;
  subtitulo: string;
  fecha: string | null;
  href: string;
  extra?: Record<string, unknown>;
  activo: boolean | null;
};

/* ───────────────────────────────────────────
   Mapeo de URLs backend → frontend
   ─────────────────────────────────────────── */
const URL_MAP: [RegExp, string][] = [
  [/^\/personal\/(\d+)$/, "/personal/personal/$1"],
  [/^\/investigadores\/(\d+)$/, "/investigadores/$1"],
  [/^\/becarios\/(\d+)$/, "/becarios/$1"],
  [/^\/actividades-docencia\/(\d+)$/, "/docenciaInvestigador/$1"],
  [/^\/documentacion-bibliografica\/(\d+)$/, "/documentacion/$1"],
  [/^\/participaciones-relevantes\/(\d+)$/, "/participaciones/$1"],
  [/^\/articulos-divulgacion\/(\d+)$/, "/articulos-divulgacion/$1"],
  [/^\/visitas-academicas\/(\d+)$/, "/visitantes/$1"],
  [/^\/proyectos\/(\d+)$/, "/proyectos/$1"],
  [/^\/transferencias\/(\d+)$/, "/transferencias/$1"],
  [/^\/distinciones\/(\d+)$/, "/distinciones/$1"],
  [/^\/equipamiento\/(\d+)$/, "/equipamiento/$1"],
  [/^\/movimientos\/(\d+)$/, "/movimientos/$1"],
  [/^\/registros-propiedad\/(\d+)$/, "/registros-propiedad/$1"],
  [/^\/trabajos-reunion-cientifica\/(\d+)$/, "/trabajos-reunion/$1"],
  [/^\/trabajos-revistas\/(\d+)$/, "/trabajos-revistas/$1"],
  [/^\/planificaciones\/(\d+)$/, "/planificaciones/$1"],

  [/^\/tipos-proyecto\/.+$/, "/proyectos"],
  [/^\/tipos-erogacion\/.+$/, "/movimientos"],
  [/^\/tipos-registro\/.+$/, "/registros-propiedad"],
  [/^\/tipos-contrato\/.+$/, "/transferencias"],
  [/^\/tipos-personal\/.+$/, "/personal"],
  [/^\/fuente-financiamiento\/.+$/, "/proyectos"],
  [/^\/fuentes-financiamiento\/.+$/, "/proyectos"],
  [/^\/autores\/.+$/, "/documentacion"],
  [/^\/directivos\/.+$/, "/personal"],
];

export function resolveFrontendUrl(backendUrl: string): string {
  if (!backendUrl.startsWith("/") || backendUrl.startsWith("//")) {
    return "/search";
  }

  for (const [re, replacement] of URL_MAP) {
    if (re.test(backendUrl)) {
      return backendUrl.replace(re, replacement);
    }
  }
  return backendUrl;
}

function isBackendResult(value: unknown): value is BackendResult {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<BackendResult>;
  return (
    typeof item.id === "number" &&
    Number.isFinite(item.id) &&
    typeof item.tipo === "string" &&
    typeof item.titulo === "string" &&
    typeof item.url === "string" &&
    (item.extra === undefined ||
      (item.extra !== null && typeof item.extra === "object" && !Array.isArray(item.extra)))
  );
}

function normalizeMeta(meta: SearchMeta | undefined, requestedPage: number): SearchMeta {
  const page = Number.isInteger(meta?.page) && (meta?.page ?? 0) > 0
    ? meta!.page
    : requestedPage;
  const total = Number.isInteger(meta?.total) && (meta?.total ?? -1) >= 0
    ? meta!.total
    : 0;
  const totalPages = Number.isInteger(meta?.total_pages) && (meta?.total_pages ?? 0) > 0
    ? meta!.total_pages
    : 1;

  return { page, per_page: 9, total, total_pages: totalPages };
}

function mapEstadoToQueryValue(estado: EstadoBusqueda): string | null {
  if (estado === "activos") return null;
  if (estado === "eliminados") return "true";
  return "all";
}

/* ───────────────────────────────────────────
   Función principal
   ─────────────────────────────────────────── */
export async function searchAll(
  q: string,
  orden: Orden = "alf_asc",
  estado: EstadoBusqueda = "activos",
  page = 1,
  signal?: AbortSignal,
): Promise<SearchPageResult> {
  const query = q.trim();
  if (query.length < 2) {
    return { results: [], meta: { page: 1, per_page: 9, total: 0, total_pages: 1 } };
  }

  if (query.length > SEARCH_MAX_QUERY_LENGTH) {
    throw new Error("El texto de busqueda es demasiado largo.");
  }

  if (!Number.isInteger(page) || page < 1) {
    throw new Error("La pagina debe ser un entero mayor a cero.");
  }

  const params = new URLSearchParams({
    q: query,
    orden,
    page: String(page),
    per_page: "9",
  });

  const eliminados = mapEstadoToQueryValue(estado);
  if (eliminados !== null) {
    params.set("eliminados", eliminados);
  }

  const data = await http<SearchResponse>(`/search/?${params.toString()}`, { signal });

  if (!Array.isArray(data?.resultados)) {
    return { results: [], meta: { page, per_page: 9, total: 0, total_pages: 1 } };
  }

  return {
    results: data.resultados.filter(isBackendResult).map((r) => ({
      id: r.id,
      tipo: r.tipo,
      titulo: r.titulo,
      subtitulo: r.subtitulo ?? "",
      fecha: r.fecha ? String(r.fecha) : null,
      href: resolveFrontendUrl(r.url),
      extra: r.extra,
      activo: typeof r.activo === "boolean" ? r.activo : null,
    })),
    meta: normalizeMeta(data.meta, page),
  };
}
