import test from "node:test";
import assert from "node:assert/strict";
import { writeSharedTiming, readNewerTiming, clearSharedTiming } from "../src/modules/auth/utils/sharedSessionTiming.ts";

class MemoryStorage {
  values = new Map<string, string>();
  get length() { return this.values.size; }
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
  clear() { this.values.clear(); }
  key(index: number) { return [...this.values.keys()][index] ?? null; }
}

test("pestana suspendida recupera tiempos mas nuevos, aislados por usuario y borrados al salir", () => {
  const storage = new MemoryStorage();
  const old = { accessExpiresAt: "2026-11-04T12:10:00Z", sessionExpiresAt: "2026-11-04T12:03:00Z", warningSeconds: 60 };
  const fresh = { ...old, sessionExpiresAt: "2026-11-04T12:06:00Z" };
  writeSharedTiming(1, fresh, storage);
  assert.deepEqual(readNewerTiming(1, old, storage), fresh);
  assert.equal(readNewerTiming(2, old, storage), old);
  assert.equal(readNewerTiming(1, fresh, storage), fresh);
  clearSharedTiming(1, storage);
  assert.equal(readNewerTiming(1, old, storage), old);
  storage.setItem("gidas:session-timing:v1:1", "malformed");
  assert.equal(readNewerTiming(1, old, storage), old);
  assert.ok(![...storage.values.values()].some(value => value.includes("access_token")));
});
