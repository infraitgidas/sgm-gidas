import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";
import { calendarValidationMessage } from "../src/utils/calendarValidation.ts";

test("calendario explica límites, formato y fechas válidas", () => {
  const min = new Date(2010, 0, 1);
  assert.match(calendarValidationMessage("01/01/2008", new Date(2008, 0, 1), min), /desde 01\/01\/2010/);
  assert.match(calendarValidationMessage("31/02/2026", null, min), /fecha válida/);
  assert.match(calendarValidationMessage("2008", null, min), /DD\/MM\/AAAA/);
  assert.equal(calendarValidationMessage("01/01/2010", min, min), "");
  assert.equal(calendarValidationMessage("", null, min), "");
  assert.match(calendarValidationMessage("02/01/2026", new Date(2026, 0, 2), undefined, new Date(2026, 0, 1)), /posteriores al 01\/01\/2026/);
});

// Ejecuta el módulo HTTP real con configuración e imports adaptados a Node.
async function loadHttp() {
  const source = readFileSync(new URL("../src/lib/http.ts", import.meta.url), "utf8")
    .replace('"./httpPolicy"', JSON.stringify(new URL("../src/lib/httpPolicy.ts", import.meta.url).href))
    .replace('"@/modules/auth/utils/singleFlight"', JSON.stringify(new URL("../src/modules/auth/utils/singleFlight.ts", import.meta.url).href))
    .replaceAll("import.meta.env", "({})");
  const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}#${Math.random()}`);
}

test("refresh preserva token ante red/500/429/403 y respuesta inválida; 401 lo invalida", async () => {
  const originalFetch = globalThis.fetch;
  const http = await loadHttp();
  try {
    for (const status of [500, 429, 403]) {
      http.setAccessToken("token-vigente");
      globalThis.fetch = async () => new Response("", { status });
      await assert.rejects(http.refreshSession());
      assert.equal(http.getAccessToken(), "token-vigente");
    }
    globalThis.fetch = async () => { throw new TypeError("offline"); };
    await assert.rejects(http.refreshSession());
    assert.equal(http.getAccessToken(), "token-vigente");
    globalThis.fetch = async () => Response.json({});
    await assert.rejects(http.refreshSession());
    assert.equal(http.getAccessToken(), "token-vigente");
    globalThis.fetch = async () => new Response("", { status: 401 });
    assert.equal(await http.refreshSession(), null);
    assert.equal(http.getAccessToken(), null);
    globalThis.fetch = async () => Response.json({ access_token: "nuevo-token" });
    assert.equal((await http.refreshSession()).access_token, "nuevo-token");
    assert.equal(http.getAccessToken(), "nuevo-token");
  } finally { globalThis.fetch = originalFetch; }
});

test("un fallo temporal de refresh tras 401 no emite expiración", async () => {
  const originalFetch = globalThis.fetch;
  const http = await loadHttp();
  try {
    http.setAccessToken("token-vigente");
    globalThis.fetch = async (url) => new Response("", { status: String(url).endsWith("/auth/refresh") ? 503 : 401 });
    // Sin window: emitir session-expired causaría ReferenceError.
    await assert.rejects(http.http("/personal"), (error: Error & { status?: number }) => error.status === 503);
    assert.equal(http.getAccessToken(), "token-vigente");
    await assert.rejects(http.httpDownload("/export"), (error: Error & { status?: number }) => error.status === 503);
  } finally { globalThis.fetch = originalFetch; }
});

test("actividad y Continuar sesión conservan sesión ante errores y permiten reintento", async () => {
  const effects: Array<() => unknown> = [];
  const states: unknown[] = [];
  const handlers = new Map<string, () => void>();
  const harness = { effects, states };
  const globals = globalThis as typeof globalThis & { window?: unknown; __sessionHarness?: typeof harness };
  const originalWindow = globals.window;
  globals.__sessionHarness = harness;
  globals.window = {
    setTimeout: () => 1, clearTimeout: () => {},
    addEventListener: (name: string, handler: () => void) => handlers.set(name, handler),
    removeEventListener: () => {},
  };
  const reactMock = `const h = globalThis.__sessionHarness;
    export const useCallback = fn => fn;
    export const useRef = current => ({current});
    export const useEffect = fn => h.effects.push(fn);
    export const useState = value => { const i = h.states.length; h.states.push(value); return [value, next => h.states[i] = next]; };`;
  const source = readFileSync(new URL("../src/modules/auth/hooks/useSessionLifecycle.ts", import.meta.url), "utf8")
    .replace('"react"', JSON.stringify(`data:text/javascript;base64,${Buffer.from(reactMock).toString("base64")}`))
    .replace('"@/modules/auth/utils/sessionTiming"', JSON.stringify(new URL("../src/modules/auth/utils/sessionTiming.ts", import.meta.url).href));
  try {
    const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
    const { useSessionLifecycle } = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);
    let expired = 0;
    let result: boolean | Error = new Error("offline");
    const lifecycle = useSessionLifecycle({
      timing: { accessExpiresAt: new Date(Date.now() + 60_000).toISOString(), sessionExpiresAt: new Date(Date.now() + 3_600_000).toISOString(), warningSeconds: 300 },
      onRefresh: async () => { if (result instanceof Error) throw result; return result; },
      onExpire: () => expired++,
    });
    effects.forEach(effect => effect());
    handlers.get("pointerdown")!();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(expired, 0);
    assert.equal(states[0], true);
    assert.match(String(states[3]), /conexión/);
    await lifecycle.extendSession();
    assert.equal(expired, 0);
    assert.equal(states[2], false);
    result = true;
    await lifecycle.extendSession();
    assert.equal(states[0], false);
    result = false;
    await lifecycle.extendSession();
    assert.equal(expired, 1);
  } finally {
    globals.window = originalWindow;
    delete globals.__sessionHarness;
  }
});
