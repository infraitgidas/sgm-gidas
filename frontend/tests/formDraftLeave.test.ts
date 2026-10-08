import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
type DraftValue = { name: string };

function createHarness(savedDraft: DraftValue | null = null, initialValue: DraftValue = { name: "" }) {
  const slots: any[] = [];
  const effects: Array<() => void> = [];
  const timers: Array<() => void> = [];
  let cursor = 0;
  let value: DraftValue = initialValue;
  let blockerPredicate = () => false;
  let saved = 0;
  let deleted = 0;
  const same = (a: unknown[] | undefined, b: unknown[]) =>
    Boolean(a && a.length === b.length && a.every((item, index) => Object.is(item, b[index])));
  const react = {
    useState(initial: unknown) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], (next: unknown) => { slots[index] = typeof next === "function" ? (next as Function)(slots[index]) : next; }];
    },
    useRef(initial: unknown) {
      const index = cursor++;
      return slots[index] ?? (slots[index] = { current: initial });
    },
    useMemo(fn: () => unknown, deps: unknown[]) {
      const index = cursor++;
      if (!same(slots[index]?.deps, deps)) slots[index] = { deps, value: fn() };
      return slots[index].value;
    },
    useCallback(fn: Function, deps: unknown[]) {
      const index = cursor++;
      if (!same(slots[index]?.deps, deps)) slots[index] = { deps, value: fn };
      return slots[index].value;
    },
    useEffect(fn: () => void, deps: unknown[]) {
      const index = cursor++;
      if (!same(slots[index]?.deps, deps)) {
        slots[index]?.cleanup?.();
        slots[index] = { deps };
        effects.push(() => { slots[index].cleanup = fn(); });
      }
    },
  };
  const source = ts.transpileModule(readFileSync("src/modules/shared/hooks/useFormDraft.ts", "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText;
  const module = { exports: {} as any };
  runInNewContext(source, {
    module, exports: module.exports, window: {
      setTimeout(fn: () => void) { timers.push(fn); return timers.length; },
      clearTimeout() {},
    },
    require(name: string) {
      if (name === "react") return react;
      if (name === "react-router-dom") return { useBlocker: (fn: () => boolean) => {
        blockerPredicate = fn;
        return { state: "unblocked" };
      } };
      if (name === "@tanstack/react-query") return { useQueryClient: () => ({ setQueryData() {}, invalidateQueries() {} }) };
      if (name === "@/modules/shared/services/formDraftService") return {
        getFormDraft: async () => savedDraft && { data: savedDraft },
        putFormDraft: async () => { saved++; return { module: "test", record_key: "new" }; },
        deleteFormDraft: async () => { deleted++; },
      };
      return require(name);
    },
  });
  const render = (recordId?: number) => {
    cursor = 0;
    const result = module.exports.useFormDraft({
      userId: 1, module: "test", recordId, value, ready: true, autosave: false,
      hasContent: (draft: DraftValue) => Boolean(draft.name),
      onRestore: (draft: DraftValue) => { value = draft; },
    });
    while (effects.length) effects.shift()?.();
    return result;
  };
  const initialize = async (recordId?: number) => {
    render(recordId);
    while (timers.length) timers.shift()?.();
    await Promise.resolve();
    return render(recordId);
  };
  return {
    render, initialize,
    setValue(next: DraftValue) { value = next; },
    get blocked() { return blockerPredicate(); },
    get saved() { return saved; },
    get deleted() { return deleted; },
  };
}

test("Volver en alta o edicion sin cambios sale directamente; cambiar y revertir restaura esa salida", async () => {
  for (const recordId of [undefined, 42]) {
    const initialName = recordId ? "Registrado" : "";
    const harness = createHarness(null, { name: initialName });
    let left = 0;
    let form = await harness.initialize(recordId);
    form.requestLeave(() => { left++; });
    assert.equal(left, 1);
    assert.equal(harness.blocked, false);
    assert.equal(harness.render(recordId).blocker.state, "unblocked");

    harness.setValue({ name: "Cambio" });
    form = harness.render(recordId);
    assert.equal(harness.blocked, true);
    form.requestLeave(() => { left++; });
    assert.equal(left, 1);
    assert.equal(harness.render(recordId).blocker.state, "blocked");

    form.blocker.reset?.();
    harness.setValue({ name: initialName });
    form = harness.render(recordId);
    assert.equal(harness.blocked, false);
    form.requestLeave(() => { left++; });
    assert.equal(left, 2);
    assert.equal(harness.saved, 0);
  }
});

test("un borrador recuperado es la nueva base y solo sus cambios posteriores piden confirmacion", async () => {
  const harness = createHarness({ name: "Recuperado" });
  let form = await harness.initialize(42);
  assert.ok(form.availableDraft);
  form.restoreDraft();
  form = harness.render(42);
  let left = 0;
  form.requestLeave(() => { left++; });
  assert.equal(left, 1);
  assert.equal(harness.blocked, false);

  harness.setValue({ name: "Otro" });
  form = harness.render(42);
  assert.equal(harness.blocked, true);
  harness.setValue({ name: "Recuperado" });
  form = harness.render(42);
  assert.equal(harness.blocked, false);
  assert.equal(harness.saved, 0);
  assert.equal(harness.deleted, 0);
});

test("guardar y descartar desde la confirmacion conservan sus acciones", async () => {
  const saving = createHarness();
  await saving.initialize();
  saving.setValue({ name: "Nuevo" });
  let form = saving.render();
  let savedLeave = 0;
  form.requestLeave(() => { savedLeave++; });
  form = saving.render();
  assert.equal(await form.keepAndLeave(), true);
  assert.equal(saving.saved, 1);
  assert.equal(savedLeave, 1);

  const discarding = createHarness();
  await discarding.initialize();
  discarding.setValue({ name: "Nuevo" });
  form = discarding.render();
  let discardedLeave = 0;
  form.requestLeave(() => { discardedLeave++; });
  form = discarding.render();
  assert.equal(await form.discardAndLeave(), true);
  assert.equal(discarding.deleted, 1);
  assert.equal(discarding.saved, 0);
  assert.equal(discardedLeave, 1);
});
