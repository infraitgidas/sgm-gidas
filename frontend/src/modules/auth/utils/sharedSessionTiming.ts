import type { SessionTiming } from "./sessionTiming";

const key = (userId: number) => `gidas:session-timing:v1:${userId}`;

export function writeSharedTiming(userId: number, timing: SessionTiming, storage: Storage = localStorage) {
  try { storage.setItem(key(userId), JSON.stringify(timing)); } catch { /* BroadcastChannel remains available. */ }
}

export function readNewerTiming(userId: number, current: SessionTiming, storage: Storage = localStorage): SessionTiming {
  try {
    const value = JSON.parse(storage.getItem(key(userId)) ?? "null");
    if (value && Number.isFinite(Date.parse(value.accessExpiresAt)) &&
        Number.isFinite(value.warningSeconds) && value.warningSeconds >= 0 &&
        Date.parse(value.sessionExpiresAt) > Date.parse(current.sessionExpiresAt)) return value;
  } catch { /* Storage is optional; it never grants access. */ }
  return current;
}

export function clearSharedTiming(userId: number, storage: Storage = localStorage) {
  try { storage.removeItem(key(userId)); } catch { /* Optional metadata. */ }
}
