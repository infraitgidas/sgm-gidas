import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

test("catalogos recupera sin sobrescribir y guarda solo despues de decidir", async () => {
  const saved = { endpoint: "/tipo-personal/", mode: "create", editId: null, name: "Pendiente", description: "", fkId: "" };
  const h = {
    slots: [] as any[], index: 0, effects: [] as Array<() => any>, deps: [] as any[],
    timers: new Map<number, () => void>(), writes: [] as any[], deleted: 0,
    draft: { data: saved, saved_at: "2026-11-04T12:00:00Z" } as any,
    client: { invalidateQueries: async () => {} },
  };
  const globals = globalThis as any;
  const previous = globals.window;
  globals.__catalogHarness = h;
  globals.window = { setTimeout: (fn: () => void) => { const id = h.timers.size + 1; h.timers.set(id, fn); return id; }, clearTimeout: (id: number) => h.timers.delete(id) };
  const dataUrl = (source: string) => `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  const react = dataUrl(`const h=globalThis.__catalogHarness;
    export const useState=v=>{const i=h.index++;if(!(i in h.slots))h.slots[i]=v;return [h.slots[i],v=>h.slots[i]=typeof v==='function'?v(h.slots[i]):v];};
    export const useRef=v=>{const i=h.index++;return h.slots[i]??=( {current:v} );};
    export const useCallback=fn=>fn;
    export const useEffect=(fn,deps)=>{const i=h.index++;const old=h.deps[i];if(!old||deps.some((v,j)=>v!==old[j])){h.deps[i]=deps;h.effects.push(fn);}};`);
  const services = dataUrl(`const h=globalThis.__catalogHarness;
    export const getFormDraft=async()=>h.draft;
    export const putFormDraft=async(m,id,value)=>{h.writes.push({m,id,value});return {};};
    export const deleteFormDraft=async()=>{h.deleted++;};`);
  const query = dataUrl(`export const useQueryClient=()=>globalThis.__catalogHarness.client;`);
  const source = readFileSync(new URL("../src/modules/catalogos/hooks/useCatalogDraft.ts", import.meta.url), "utf8")
    .replace('"react"', JSON.stringify(react))
    .replace('"@tanstack/react-query"', JSON.stringify(query))
    .replace('"@/modules/shared/services/formDraftService"', JSON.stringify(services));
  try {
    const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
    const { useCatalogDraft } = await import(dataUrl(js));
    const render = () => { h.index=0; const result=useCatalogDraft(1,true); h.effects.splice(0).forEach(fn=>fn()); return result; };
    render();
    await new Promise(resolve=>setImmediate(resolve));
    let result=render();
    assert.deepEqual(result.available.data, saved);
    assert.equal(result.ready,false);
    result.setValue({...saved,name:"Edicion accidental"});
    render();
    assert.equal(h.timers.size,0,"un borrador pendiente de recuperacion no se sobrescribe");
    result.restore();
    result.setValue({...saved,name:"Recuperado y editado"});
    render();
    for(const fn of h.timers.values())fn();
    h.timers.clear();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(h.writes.length,1);
    assert.equal(h.writes[0].m,"catalogos");
    assert.equal(h.writes[0].value.name,"Recuperado y editado");
    result=render();
    await result.clear();
    result=render();
    assert.equal(h.deleted,1);
    assert.equal(result.available,null);
    assert.equal(result.ready,true);
  } finally { globals.window=previous; delete globals.__catalogHarness; }
});
