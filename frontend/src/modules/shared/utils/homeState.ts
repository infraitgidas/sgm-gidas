export type HomeValueOptions = {
  allowed?: readonly unknown[];
  shape?: Record<string, unknown>;
  kind?: "id" | "text";
};

const PREFIX = "gidas:homes:v1:";

export function homeStateKey(userId: number | undefined, scope: string, field: string): string | null {
  return userId && Number.isSafeInteger(userId)
    ? `${PREFIX}${userId}:${scope}:${field}` : null;
}

function matchesShape(value: unknown, initial: unknown): boolean {
  if (initial === undefined) return value === null || typeof value === "string" && value.length <= 500
    || typeof value === "number" && Number.isSafeInteger(value) && value > 0;
  if (typeof initial === "string") return typeof value === "string" && value.length <= 500;
  if (typeof initial === "number") return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
  if (initial && typeof initial === "object" && !Array.isArray(initial)) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const shape = initial as Record<string, unknown>;
    return Object.entries(value).every(([key, item]) => Object.prototype.hasOwnProperty.call(shape, key) && matchesShape(item, shape[key]));
  }
  return false;
}

export function readHomeValue<T>(storage: Storage | undefined, key: string | null, field: string,
  initial: T, options: HomeValueOptions = {}): T {
  if (!key || !storage) return initial;
  try {
    const raw = storage.getItem(key);
    if (!raw || raw.length > 10000) return initial;
    const value: unknown = JSON.parse(raw);
    if (!matchesShape(value, options.shape ?? initial)) return initial;
    if (value !== null && options.kind === "id" && !(typeof value === "number" && value > 0)) return initial;
    if (value !== null && options.kind === "text" && typeof value !== "string") return initial;
    if (options.allowed && !options.allowed.includes(value)) return initial;
    if (/^(page|currentPage|fuentesPage)$/.test(field) && !(typeof value === "number" && value > 0)) return initial;
    if (initial && typeof initial === "object" && !Array.isArray(initial)) return { ...initial, ...value as object };
    return (value === null && initial === undefined ? undefined : value) as T;
  } catch { return initial; }
}

export function writeHomeValue(storage: Storage | undefined, key: string | null, value: unknown): void {
  if (!key || !storage) return;
  try { storage.setItem(key, JSON.stringify(value ?? null)); } catch { /* La consulta sigue disponible sin persistencia. */ }
}

export function homeStorage(): Storage | undefined {
  try { return window.sessionStorage; } catch { return undefined; }
}
