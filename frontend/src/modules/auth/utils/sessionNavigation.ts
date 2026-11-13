const RETURN_PATH_KEY = "gidas:auth:return-path:v1";
const ACTIVE_SESSION_KEY = "gidas:auth:active-session:v1";
const SESSION_ENDED_KEY = "gidas:auth:session-ended:v1";
const SESSION_OWNER_KEY = "gidas:auth:session-owner:v1";
const RETURN_CONTEXT_KEY = "gidas:auth:return-context:v1";

export function markSessionActive(storage: Storage = sessionStorage, userId?: number) {
  storage.setItem(ACTIVE_SESSION_KEY, "1");
  if (userId) storage.setItem(SESSION_OWNER_KEY, String(userId));
  storage.removeItem(SESSION_ENDED_KEY);
}

export function markSessionEnded(storage: Storage = sessionStorage) {
  if (storage.getItem(ACTIVE_SESSION_KEY)) storage.setItem(SESSION_ENDED_KEY, "1");
  storage.removeItem(ACTIVE_SESSION_KEY);
}

export function clearSessionNotice(storage: Storage = sessionStorage) {
  storage.removeItem(ACTIVE_SESSION_KEY);
  storage.removeItem(SESSION_ENDED_KEY);
  storage.removeItem(SESSION_OWNER_KEY);
  clearSessionReturn(storage);
}

export function consumeSessionEnded(storage: Storage = sessionStorage): boolean {
  const ended = storage.getItem(SESSION_ENDED_KEY) === "1";
  storage.removeItem(SESSION_ENDED_KEY);
  return ended;
}

export function isSafeInternalPath(path: string): boolean {
  return path.startsWith("/") && !path.startsWith("//") && !path.includes("\\");
}

export function rememberSessionPath(path: string, storage: Storage = sessionStorage, state?: unknown,
  userId = readSessionOwner(storage)) {
  if (isSafeInternalPath(path) && !path.startsWith("/login")) {
    storage.setItem(RETURN_PATH_KEY, path);
    storage.setItem(RETURN_CONTEXT_KEY, JSON.stringify({
      userId, state: sessionNavigationState(state),
    }));
  }
}

export function consumeSessionPath(storage: Storage = sessionStorage): string | null {
  const path = storage.getItem(RETURN_PATH_KEY);
  clearSessionReturn(storage);
  return path && isSafeInternalPath(path) ? path : null;
}

export function readSessionOwner(storage: Storage = sessionStorage): number | undefined {
  const value = Number(storage.getItem(SESSION_OWNER_KEY));
  return Number.isSafeInteger(value) && value > 0 ? value : undefined;
}

/** Conserva únicamente el contexto de consulta de Memorias, sin mensajes ni acciones. */
export function sessionNavigationState(state: unknown): { memoriaFilter: Record<string, unknown> } | undefined {
  if (!state || typeof state !== "object") return undefined;
  const filter = (state as Record<string, unknown>).memoriaFilter;
  if (!filter || typeof filter !== "object") return undefined;
  const f = filter as Record<string, unknown>;
  if (f.source !== "memoria" || ![f.memoriaId, f.versionId].every(v => typeof v === "number" && Number.isSafeInteger(v) && v > 0)
    || ![f.sectionKey, f.sectionLabel, f.memoriaLabel].every(v => typeof v === "string" && v.length <= 500)
    || !Array.isArray(f.ids) || f.ids.length > 10000
    || !f.ids.every(v => typeof v === "number" && Number.isSafeInteger(v) && v > 0 || typeof v === "string" && /^[\w-]{1,80}$/.test(v))) return undefined;
  return { memoriaFilter: {
    source: "memoria", sectionKey: f.sectionKey, sectionLabel: f.sectionLabel, ids: f.ids,
    memoriaLabel: f.memoriaLabel, memoriaId: f.memoriaId, versionId: f.versionId,
  } };
}

export type SessionReturn = { path: string; userId?: number; state?: ReturnType<typeof sessionNavigationState> };

export function readSessionReturn(storage: Storage = sessionStorage): SessionReturn | null {
  const path = storage.getItem(RETURN_PATH_KEY);
  if (!path || !isSafeInternalPath(path) || path.startsWith("/login")) return null;
  try {
    const context = JSON.parse(storage.getItem(RETURN_CONTEXT_KEY) ?? "{}");
    return { path, userId: Number.isSafeInteger(context.userId) && context.userId > 0 ? context.userId : readSessionOwner(storage),
      state: sessionNavigationState(context.state) };
  } catch { return { path, userId: readSessionOwner(storage) }; }
}

export function resolveSessionReturn(destination: SessionReturn, userId: number): SessionReturn {
  return destination.userId && destination.userId !== userId || !isSafeInternalPath(destination.path)
    ? { path: "/inicio" } : destination;
}

export function clearSessionReturn(storage: Storage = sessionStorage): void {
  storage.removeItem(RETURN_PATH_KEY);
  storage.removeItem(RETURN_CONTEXT_KEY);
}
