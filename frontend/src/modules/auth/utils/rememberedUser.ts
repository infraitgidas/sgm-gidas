const KEY = "gidas:auth:remembered-user:v1";

function browserStorage(): Storage | undefined {
  try { return window.localStorage; } catch { return undefined; }
}

export function readRememberedUser(storage = browserStorage()): string {
  try {
    const raw = storage?.getItem(KEY);
    if (!raw || raw.length > 500) return "";
    const data = JSON.parse(raw);
    return typeof data?.username === "string" && data.username.trim().length > 0
      && data.username.length <= 80 && !/[\u0000-\u001f\u007f]/.test(data.username) ? data.username : "";
  } catch { return ""; }
}

export function forgetRememberedUser(storage = browserStorage()): void {
  try { storage?.removeItem(KEY); } catch { /* La preferencia no condiciona el acceso. */ }
}

export function rememberUser(username: string, storage = browserStorage()): void {
  const value = username.trim();
  if (!value || value.length > 80 || /[\u0000-\u001f\u007f]/.test(value)) return forgetRememberedUser(storage);
  try { storage?.setItem(KEY, JSON.stringify({ username: value })); } catch { /* Sin persistencia, se mantiene el login. */ }
}
