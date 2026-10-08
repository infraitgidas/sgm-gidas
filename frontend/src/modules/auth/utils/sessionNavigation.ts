const RETURN_PATH_KEY = "gidas:auth:return-path:v1";
const ACTIVE_SESSION_KEY = "gidas:auth:active-session:v1";
const SESSION_ENDED_KEY = "gidas:auth:session-ended:v1";

export function markSessionActive(storage: Storage = sessionStorage) {
  storage.setItem(ACTIVE_SESSION_KEY, "1");
  storage.removeItem(SESSION_ENDED_KEY);
}

export function markSessionEnded(storage: Storage = sessionStorage) {
  if (storage.getItem(ACTIVE_SESSION_KEY)) storage.setItem(SESSION_ENDED_KEY, "1");
  storage.removeItem(ACTIVE_SESSION_KEY);
}

export function clearSessionNotice(storage: Storage = sessionStorage) {
  storage.removeItem(ACTIVE_SESSION_KEY);
  storage.removeItem(SESSION_ENDED_KEY);
}

export function consumeSessionEnded(storage: Storage = sessionStorage): boolean {
  const ended = storage.getItem(SESSION_ENDED_KEY) === "1";
  storage.removeItem(SESSION_ENDED_KEY);
  return ended;
}

export function isSafeInternalPath(path: string): boolean {
  return path.startsWith("/") && !path.startsWith("//") && !path.includes("\\");
}

export function rememberSessionPath(path: string, storage: Storage = sessionStorage) {
  if (isSafeInternalPath(path) && !path.startsWith("/login")) {
    storage.setItem(RETURN_PATH_KEY, path);
  }
}

export function consumeSessionPath(storage: Storage = sessionStorage): string | null {
  const path = storage.getItem(RETURN_PATH_KEY);
  storage.removeItem(RETURN_PATH_KEY);
  return path && isSafeInternalPath(path) ? path : null;
}
