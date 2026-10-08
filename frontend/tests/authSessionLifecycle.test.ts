import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createSingleFlight } from "../src/modules/auth/utils/singleFlight.ts";
import {
  remainingSessionSeconds,
  shouldRefreshAfterActivity,
  shouldWarnSession,
} from "../src/modules/auth/utils/sessionTiming.ts";
import {
  clearSessionNotice,
  consumeSessionEnded,
  consumeSessionPath,
  markSessionActive,
  markSessionEnded,
  rememberSessionPath,
} from "../src/modules/auth/utils/sessionNavigation.ts";

const httpSource = readFileSync(new URL("../src/lib/http.ts", import.meta.url), "utf8");
const dialogSource = readFileSync(
  new URL("../src/modules/auth/components/SessionExpiryDialog.tsx", import.meta.url),
  "utf8"
);

class MemoryStorage implements Storage {
  private values = new Map<string, string>();
  get length() { return this.values.size; }
  clear() { this.values.clear(); }
  getItem(key: string) { return this.values.get(key) ?? null; }
  key(index: number) { return [...this.values.keys()][index] ?? null; }
  removeItem(key: string) { this.values.delete(key); }
  setItem(key: string, value: string) { this.values.set(key, value); }
}

test("varias renovaciones concurrentes comparten una sola solicitud activa", async () => {
  let calls = 0;
  const renew = createSingleFlight(async () => {
    calls += 1;
    await Promise.resolve();
    return "nuevo-token";
  });

  const results = await Promise.all([renew(), renew(), renew()]);
  assert.deepEqual(results, ["nuevo-token", "nuevo-token", "nuevo-token"]);
  assert.equal(calls, 1);
  assert.match(httpSource, /createSingleFlight/);
  assert.match(httpSource, /res\.status === 401 && !_isRetry/);
  assert.match(httpSource, /http<T>\(path, init, true\)/);
});

test("el aviso y la renovacion por actividad respetan los umbrales", () => {
  const now = Date.parse("2026-09-10T12:00:00Z");
  const timing = {
    accessExpiresAt: "2026-09-10T12:01:00Z",
    sessionExpiresAt: "2026-09-10T12:04:00Z",
    warningSeconds: 300,
  };

  assert.equal(shouldWarnSession(timing, now), true);
  assert.equal(shouldRefreshAfterActivity(timing, now), true);
  assert.equal(remainingSessionSeconds(timing, now), 240);
  assert.match(dialogSource, /Continuar sesión/);
  assert.match(dialogSource, /Cerrar sesión/);
  assert.match(dialogSource, /aria-busy=\{extending\}/);
  assert.match(dialogSource, /Continuar sesión\s+\{extending && \(/);
  assert.match(dialogSource, /inline-flex items-center gap-2/);
});

test("la ruta interna se conserva una vez y descarta destinos externos", () => {
  const storage = new MemoryStorage();
  rememberSessionPath("/proyectos/7/editar?tab=equipo#form", storage);
  assert.equal(consumeSessionPath(storage), "/proyectos/7/editar?tab=equipo#form");
  assert.equal(consumeSessionPath(storage), null);

  rememberSessionPath("//sitio-externo.example", storage);
  assert.equal(consumeSessionPath(storage), null);
});

test("una recarga con refresh revocado muestra un aviso de sesión terminada una sola vez", () => {
  const storage = new MemoryStorage();
  markSessionActive(storage);
  markSessionEnded(storage);
  assert.equal(consumeSessionEnded(storage), true);
  assert.equal(consumeSessionEnded(storage), false);
  markSessionActive(storage);
  clearSessionNotice(storage);
  markSessionEnded(storage);
  assert.equal(consumeSessionEnded(storage), false);
});

test("la expiracion durante una edicion conserva la ruta hasta el nuevo login", () => {
  const storage = new MemoryStorage();
  rememberSessionPath("/proyectos/7/editar", storage);

  assert.equal(consumeSessionPath(storage), "/proyectos/7/editar");
});
