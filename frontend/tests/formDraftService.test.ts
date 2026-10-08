import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

type Request = { path: string; options?: Record<string, unknown> };

test("borradores usa el contrato HTTP y conserva solo la ultima version del elemento", async () => {
  const requests: Request[] = [];
  const stored = new Map<string, unknown>();
  const http = async (path: string, options?: Record<string, unknown>) => {
    requests.push({ path, options });
    if (options?.method === "PUT") {
      stored.set(path, JSON.parse(String(options.body)).data);
      return { data: { module: "proyectos", record_key: "new" } };
    }
    if (options?.method === "DELETE") {
      stored.delete(path);
      return { data: { deleted: true } };
    }
    if (path === "/borradores") return { data: [] };
    const data = stored.get(path);
    return data ? { data: { module: "proyectos", record_key: "new", data } } : null;
  };
  const module = { exports: {} as Record<string, any> };
  const code = ts.transpileModule(readFileSync("src/modules/shared/services/formDraftService.ts", "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  runInNewContext(code, { module, exports: module.exports, require: () => ({ http }) });
  const service = module.exports;

  assert.deepEqual(await service.listFormDrafts(), []);
  await service.putFormDraft("proyectos", undefined, { titulo: "Primero" }, "base-1");
  await service.putFormDraft("proyectos", undefined, { titulo: "Ultimo" }, "base-1");
  assert.equal(stored.size, 1);
  const draft = await service.getFormDraft("proyectos");
  assert.deepEqual(draft.data, { titulo: "Ultimo" });
  assert.equal(draft.base_fingerprint, "base-1");
  assert.equal(requests[1].path, "/borradores/proyectos/new");
  await service.deleteFormDraft("proyectos");
  assert.equal(await service.getFormDraft("proyectos"), null);
  assert.equal(stored.size, 0);
});
