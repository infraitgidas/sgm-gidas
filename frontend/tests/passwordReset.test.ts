import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { forgetRememberedUser, readRememberedUser, rememberUser } from "../src/modules/auth/utils/rememberedUser.ts";
import { isInvalidResetToken, normalizeResetEmail, parseResetFragment, takeResetToken, validateResetEmail, validateResetPassword } from "../src/modules/auth/utils/passwordReset.ts";

class MemoryStorage implements Storage {
  values = new Map<string, string>();
  get length() { return this.values.size; }
  clear() { this.values.clear(); }
  getItem(key: string) { return this.values.get(key) ?? null; }
  key(index: number) { return [...this.values.keys()][index] ?? null; }
  removeItem(key: string) { this.values.delete(key); }
  setItem(key: string, value: string) { this.values.set(key, value); }
}

test("cerrar sesion revoca acceso y conserva el usuario recordado incluso sin conexion", async () => {
  const stub = `export let token = "access"; export let calls = 0; export let failing = false;
    export function clearAccessToken() { token = null; }
    export function setAccessToken(value) { token = value; }
    export function setFailure(value) { failing = value; }
    export async function http() { calls++; if (failing) throw Error("offline"); }
    export async function refreshSession() {} export async function withAuthCookieLock(action) { return action(); }
    export class HttpError extends Error {}`;
  const stubUrl = `data:text/javascript;base64,${Buffer.from(stub).toString("base64")}#remembered-user`;
  const source = readFileSync(new URL("../src/modules/auth/services/authService.ts", import.meta.url), "utf8")
    .replace('"@/lib/http"', JSON.stringify(stubUrl));
  const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  const service = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);
  const http = await import(stubUrl);
  const storage = new MemoryStorage();
  const oldWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", { configurable: true, value: { localStorage: storage } });
  try {
    rememberUser("test.user");
    await service.logout();
    assert.equal(http.token, null); assert.equal(http.calls, 1);
    assert.equal(readRememberedUser(), "test.user");
    http.setAccessToken("new-access"); http.setFailure(true);
    await service.logout();
    assert.equal(http.token, null); assert.equal(http.calls, 2);
    assert.equal(readRememberedUser(), "test.user");
    forgetRememberedUser(); assert.equal(readRememberedUser(), "");
  } finally {
    if (oldWindow) Object.defineProperty(globalThis, "window", oldWindow);
    else Reflect.deleteProperty(globalThis, "window");
  }
});

test("recordar guarda solo nombre y permite olvidarlo sin tocar otros datos", () => {
  const storage = new MemoryStorage(); storage.setItem("other", "keep");
  rememberUser(" test.user ", storage);
  assert.equal(readRememberedUser(storage), "test.user");
  assert.equal(storage.getItem("gidas:auth:remembered-user:v1"), '{"username":"test.user"}');
  forgetRememberedUser(storage);
  assert.equal(readRememberedUser(storage), ""); assert.equal(storage.getItem("other"), "keep");
});

test("preferencias corruptas o almacenamiento bloqueado no impiden acceso", () => {
  const storage = new MemoryStorage();
  for (const value of ["{", "null", '{"username":42}', '{"username":"bad\\nname"}', "x".repeat(501)]) {
    storage.setItem("gidas:auth:remembered-user:v1", value); assert.equal(readRememberedUser(storage), "");
  }
  const blocked = { getItem() { throw Error(); }, setItem() { throw Error(); }, removeItem() { throw Error(); } } as unknown as Storage;
  assert.equal(readRememberedUser(blocked), "");
  assert.doesNotThrow(() => rememberUser("user", blocked)); assert.doesNotThrow(() => forgetRememberedUser(blocked));
});

test("email y contraseñas se validan antes de solicitar o confirmar", () => {
  assert.equal(normalizeResetEmail(" Test@Example.COM "), "test@example.com");
  assert.deepEqual(validateResetEmail(" Test@Example.COM "), {});
  for (const email of ["", "invalid", "x\n@example.com"]) assert.ok(validateResetEmail(email).email);
  assert.ok(validateResetPassword("short", "short").password_nueva);
  assert.ok(validateResetPassword("abcdef", "other").password_confirmacion);
  assert.ok(validateResetPassword("😀".repeat(19), "😀".repeat(19)).password_nueva);
  assert.deepEqual(validateResetPassword("123456", "123456"), {});
});

test("el token se captura del fragmento y se elimina conservando historial", () => {
  const token = "a".repeat(43); const state = { key: "router-key", idx: 2 };
  const location = { hash: `#token=${token}`, pathname: "/restablecer-password", search: "?origin=mail" };
  let replaced: unknown[] = [];
  const history = { state, replaceState(...args: unknown[]) { replaced = args; location.hash = ""; } };
  assert.equal(takeResetToken(location, history), token);
  assert.deepEqual(replaced, [state, "", "/restablecer-password?origin=mail"]);
  assert.equal(takeResetToken(location, history), null);
  for (const hash of ["", "#token=bad", `#token=${token}&token=${token}`, `#token=${"x".repeat(501)}`]) assert.equal(parseResetFragment(hash), null);
  assert.equal(isInvalidResetToken({ body: { error: { code: "INVALID_PASSWORD_RESET_TOKEN" } } }), true);
  assert.equal(isInvalidResetToken(null), false);
});
