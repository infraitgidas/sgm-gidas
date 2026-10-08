import { allowsNotFound, type HttpRequestInit } from "./httpPolicy";
import { createSingleFlight } from "@/modules/auth/utils/singleFlight";

const RAW_BASE =
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? "";

const LEGACY_PATH_PREFIXES: Array<[string, string]> = [
  ["/actividades-docencia", "/produccion/actividades-docencia"],
  ["/adoptantes", "/transferencia/adoptantes"],
  ["/articulos-divulgacion", "/produccion/articulos-divulgacion"],
  ["/autores", "/produccion/autores"],
  ["/becas", "/recursos/becas"],
  ["/becarios", "/personal/becarios"],
  ["/cargos", "/grupo/cargos"],
  ["/categoria-utn", "/catalogos/categoria-utn"],
  ["/directivos", "/grupo/directivos"],
  ["/distinciones", "/produccion/distinciones"],
  ["/documentacion-bibliografica", "/produccion/documentacion-bibliografica"],
  ["/equipamiento", "/recursos/equipamiento"],
  ["/fuente-financiamiento", "/catalogos/fuente-financiamiento"],
  ["/grado-academico", "/produccion/grado-academico"],
  ["/grupos-utn", "/grupo/grupo-utn"],
  ["/grupo-utn", "/grupo/grupo-utn"],
  ["/investigadores", "/personal/investigadores"],
  ["/participaciones-relevantes", "/proyectos/participaciones-relevantes"],
  ["/personal-all", "/personal/all"],
  ["/planificaciones", "/grupo/planificaciones"],
  ["/programas-incentivos", "/grupo/programas-incentivos"],
  ["/registros-propiedad", "/produccion/registros-propiedad"],
  ["/rol-actividad", "/produccion/rol-actividad"],
  ["/tipo-contrato", "/transferencia/tipo-contrato"],
  ["/tipo-dedicacion", "/personal/tipo-dedicacion"],
  ["/tipo-erogacion", "/recursos/tipo-erogacion"],
  ["/tipo-formacion", "/personal/tipo-formacion"],
  ["/tipo-personal", "/personal/tipo-personal"],
  ["/tipo-registro-propiedad", "/produccion/tipo-registro-propiedad"],
  ["/tipos-proyecto", "/proyectos/tipos-proyecto"],
  ["/tipos-reunion-cientifica", "/produccion/tipos-reunion-cientifica"],
  ["/tipos-revista", "/produccion/tipos-revista"],
  ["/trabajos-reunion-cientifica", "/produccion/trabajos-reunion-cientifica"],
  ["/trabajos-revistas", "/produccion/trabajos-revistas"],
  ["/transferencias", "/transferencia/transferencias"],
  ["/visitas-academicas", "/grupo/visitas-academicas"],
];

function normalizeBase(base: string) {
  const trimmed = base.replace(/\/+$/, "");
  if (!trimmed) return "";
  if (trimmed.endsWith("/api/v1")) return trimmed;
  if (trimmed.endsWith("/api")) return `${trimmed}/v1`;
  return `${trimmed}/api/v1`;
}

function normalizeApiPath(path: string) {
  if (path.startsWith("/api/v1/") || path === "/api/v1") {
    return path.replace(/^\/api\/v1/, "");
  }

  for (const [legacyPrefix, canonicalPrefix] of LEGACY_PATH_PREFIXES) {
    const matchesPrefix =
      path === legacyPrefix ||
      path.startsWith(`${legacyPrefix}/`) ||
      path.startsWith(`${legacyPrefix}?`);

    if (matchesPrefix) {
      return `${canonicalPrefix}${path.slice(legacyPrefix.length)}`;
    }
  }

  return path;
}

const BASE = normalizeBase(RAW_BASE);

let accessToken: string | null = null;
let sessionGeneration = 0;

export function setAccessToken(token: string | null) {
  sessionGeneration += 1;
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function clearAccessToken() {
  sessionGeneration += 1;
  accessToken = null;
}

export class HttpError extends Error {
  status: number;
  body?: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export type RefreshSessionResponse<TUser = unknown> = {
  access_token: string;
  access_expires_at: string;
  session_expires_at: string;
  session_warning_seconds: number;
  user?: TUser;
  usuario?: TUser;
};

export async function withAuthCookieLock<T>(
  operation: () => Promise<T>
): Promise<T> {
  if ("locks" in navigator) {
    return navigator.locks.request("gidas-auth-refresh", operation);
  }

  return operation();
}

const runRefreshSingleFlight = createSingleFlight(
  async (generationAtStart: number): Promise<RefreshSessionResponse | null> => {
    const performRefresh = async (): Promise<RefreshSessionResponse | null> => {
      if (generationAtStart !== sessionGeneration) return null;

    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
      });

      if (generationAtStart !== sessionGeneration) return null;

      if (!res.ok) {
        if (res.status === 401) {
          accessToken = null;
          return null;
        }
        throw new HttpError(res.status, "No pudimos renovar la sesión. Intente nuevamente.");
      }

      const data = (await res.json()) as RefreshSessionResponse;
      if (generationAtStart !== sessionGeneration) return null;

      if (typeof data.access_token === "string" && data.access_token) {
        accessToken = data.access_token;
        return data;
      }

      throw new HttpError(502, "No pudimos verificar la respuesta de sesión. Intente nuevamente.");
    } catch (error) {
      if (generationAtStart !== sessionGeneration) return null;
      throw error;
    }
    };

    return withAuthCookieLock(performRefresh);
  }
);

export async function refreshSession<TUser = unknown>(): Promise<
  RefreshSessionResponse<TUser> | null
> {
  return runRefreshSingleFlight(sessionGeneration) as Promise<
    RefreshSessionResponse<TUser> | null
  >;
}

function buildHeaders(init?: RequestInit) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) || {}),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  return headers;
}

async function parseErrorResponse(res: Response): Promise<unknown> {
  try {
    const contentType = res.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      return await res.json();
    }

    const text = await res.text();
    return text || null;
  } catch {
    return null;
  }
}

export async function http<T>(
  path: string,
  init: HttpRequestInit = {},
  _isRetry = false
): Promise<T> {
  const url = `${BASE}${normalizeApiPath(path)}`;

  const { allowNotFound, ...requestInit } = init;

  const headers = buildHeaders(requestInit);

  const res = await fetch(url, {
    ...requestInit,
    headers,
    credentials: requestInit.credentials ?? "same-origin",
  });

  if (res.status === 204) return undefined as T;
  if (res.status === 404 && allowsNotFound({ ...requestInit, allowNotFound })) {
    return null as T;
  }

  if (res.status === 401 && !_isRetry) {
    const refreshed = await refreshSession();
    if (refreshed?.access_token) {
      return http<T>(path, init, true);
    }

    window.dispatchEvent(new Event("gidas:session-expired"));
  }

  let data: unknown;
  try {
    data = await res.json();
  } catch {
    if (res.ok) return undefined as T;
  }

  if (!res.ok) {
    throw new HttpError(res.status, res.statusText, data);
  }

  return data as T;
}

export async function httpDownload(
  path: string,
  init: RequestInit = {},
  _isRetry = false
): Promise<Response> {
  const url = `${BASE}${normalizeApiPath(path)}`;

  const headers = buildHeaders({
    ...init,
    headers: {
      Accept:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/octet-stream",
      ...((init.headers as Record<string, string>) || {}),
    },
  });

  if (headers["Content-Type"] && (!init.body || init.method === "GET")) {
    delete headers["Content-Type"];
  }

  const res = await fetch(url, {
    ...init,
    headers,
    credentials: init.credentials ?? "same-origin",
  });

  if (res.status === 401 && !_isRetry) {
    const refreshed = await refreshSession();
    if (refreshed?.access_token) {
      return httpDownload(path, init, true);
    }

    window.dispatchEvent(new Event("gidas:session-expired"));
  }

  if (!res.ok) {
    const data = await parseErrorResponse(res);
    throw new HttpError(res.status, res.statusText, data);
  }

  return res;
}
