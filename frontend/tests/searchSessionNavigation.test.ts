import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

function load(file: string, dependencies: Record<string, unknown>, globals: Record<string, unknown> = {}) {
  const code = ts.transpileModule(readFileSync(file, "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText;
  const module = { exports: {} as any };
  runInNewContext(code, { module, exports: module.exports, URLSearchParams, AbortController, DOMException,
    ...globals, require(name: string) {
      if (!(name in dependencies)) throw new Error(`Unexpected dependency: ${name}`);
      return dependencies[name];
    } });
  return module.exports;
}


function harness(initialParams = "q=alpha&page=2", initialGroup: number | null = 1) {
  const slots: any[] = [];
  let cursor = 0;
  const effects: Array<() => void> = [];
  const timers = new Map<number, () => void>();
  const pending: Array<{ args: any[]; resolve: (value: any) => void }> = [];
  let timerId = 0;
  let token = "session-one", groupId = initialGroup ?? undefined;
  const params = new URLSearchParams(initialParams);
  const setSearchParams = () => {};
  const same = (a: any[] | undefined, b: any[]) => Boolean(a && a.length === b.length && a.every((x, i) => Object.is(x, b[i])));
  const react = {
    useState(initial: any) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], (value: any) => { slots[index] = typeof value === "function" ? value(slots[index]) : value; }];
    },
    useMemo(fn: () => any) { return fn(); },
    useRef(initial: any) { const index = cursor++; return slots[index] ?? (slots[index] = { current: initial }); },
    useCallback(fn: any, deps: any[]) {
      const index = cursor++;
      if (!same(slots[index]?.deps, deps)) slots[index] = { deps, value: fn };
      return slots[index].value;
    },
    useEffect(fn: any, deps: any[]) {
      const index = cursor++;
      if (!same(slots[index]?.deps, deps)) {
        slots[index]?.cleanup?.(); slots[index] = { deps };
        effects.push(() => { slots[index].cleanup = fn(); });
      }
    },
  };
  const hook = load("src/modules/search/hooks/useSearch.ts", {
    react, "react-router-dom": { useSearchParams: () => [params, setSearchParams] },
    "@/context/AuthContext": { useAuth: () => ({ user: { id: 1 }, token }) },
    "@/modules/grupo/hooks/useUct": { useUct: () => ({ uct: { id: groupId } }) },
    "@/lib/httpError": { getErrorMessage: (_error: unknown, fallback: string) => fallback },
    "@/modules/search/services/searchService": { searchAll: (...args: any[]) => new Promise((resolve) => pending.push({ args, resolve })) },
  }, { window: { setTimeout(fn: () => void, delay: number) { assert.equal(delay, 400); timers.set(++timerId, fn); return timerId; },
    clearTimeout(id: number) { timers.delete(id); } } });
  const render = () => { cursor = 0; const result = hook.useSearch(); while (effects.length) effects.shift()?.(); return result; };
  return { render, pending,
    fire() { const callbacks = [...timers.values()]; timers.clear(); callbacks.forEach((fn) => fn()); },
    changeScope() { token = "session-two"; groupId = 2; },
    refreshToken() { token = "session-refreshed"; },
    resolveGroup() { groupId = 1; },
  };
}

test("la carga inicial de UCT y renovación de token conservan la página de la URL recuperada", () => {
  const view = harness("q=alpha&page=3", null);
  assert.equal(view.render().page, 3);
  view.resolveGroup();
  assert.equal(view.render().page, 3);
  view.refreshToken();
  view.render();
  assert.equal(view.render().page, 3);
});

test("un cambio real de UCT reinicia la pagina de busqueda", () => {
  const view = harness("q=alpha&page=3");
  assert.equal(view.render().page, 3);
  view.changeScope();
  view.render();
  assert.equal(view.render().page, 1);
});
