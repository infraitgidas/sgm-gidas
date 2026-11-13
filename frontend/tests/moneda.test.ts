import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import ts from "typescript";
import { formatImporte, formatImporteHistorial, isMoneda } from "../src/utils/money.ts";

test("distingue ARS y USD sin convertir el importe original", () => {
  assert.match(formatImporte(1234.5, "ARS"), /ARS\s+1\.234,50/);
  assert.match(formatImporte(1234.5, "USD"), /USD\s+1\.234,50/);
  assert.match(formatImporte(0, "USD"), /USD\s+0,00/);
  assert.equal(formatImporte(null, "USD"), "-");
  assert.equal(formatImporte(Number.NaN, "ARS"), "-");
  assert.equal(formatImporteHistorial(1234.5), "1.234,50");
  assert.equal(formatImporteHistorial(null), "-");
  assert.equal(isMoneda("ARS"), true);
  assert.equal(isMoneda("USD"), true);
  assert.equal(isMoneda("EUR"), false);
  assert.equal(isMoneda(null), false);
});

for (const config of [
  { file: "recursos/services/equipamientoServices.ts", create: "createEquipamiento", update: "updateEquipamiento", get: "getEquipamientoById", amount: "monto_invertido" },
  { file: "transferencia/services/transferenciasServices.ts", create: "createTransferencia", update: "updateTransferencia", get: "getTransferenciaById", amount: "monto" },
]) {
  test(`${config.file}: conserva moneda al guardar y recuperar y envía solo diferencias`, async () => {
    const requests: { path: string; options?: { body?: string } }[] = [];
    let stored: Record<string, unknown> = { id: 1, [config.amount]: 100.25, moneda: "USD" };
    const module = { exports: {} as Record<string, (...args: any[]) => Promise<any>> };
    const code = ts.transpileModule(readFileSync(`src/modules/${config.file}`, "utf8"), {
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
    }).outputText;
    runInNewContext(code, { module, exports: module.exports, require(name: string) {
      if (name === "./tiposContratoService") return { isMockMode: () => false };
      if (name === "@/lib/http") return { http: async (path: string, options?: { body?: string }) => {
        requests.push({ path, options });
        if (options?.body) stored = { ...stored, ...JSON.parse(options.body) };
        return stored;
      } };
      throw new Error(`Import inesperado: ${name}`);
    } });
    const created = await module.exports[config.create]({ [config.amount]: 100.25, moneda: "USD" });
    assert.equal(created.moneda, "USD");
    assert.equal(created[config.amount], 100.25);
    assert.equal(JSON.parse(requests[0].options!.body!).moneda, "USD");
    const updated = await module.exports[config.update](1, { moneda: "ARS" });
    assert.deepEqual(JSON.parse(requests[1].options!.body!), { moneda: "ARS" });
    assert.equal(updated.moneda, "ARS");
    assert.equal(updated[config.amount], 100.25);
    stored = { id: 1, [config.amount]: 23 };
    assert.equal((await module.exports[config.get](1)).moneda, "ARS");
  });
}

for (const name of ["Equipamiento", "Transferencias"]) {
  test(`${name}: ARS por defecto no crea un borrador vacío y recupera borradores anteriores`, () => {
    const moduleName = name === "Equipamiento" ? "recursos" : "transferencia";
    const file = `src/modules/${moduleName}/pages/${name}Form.tsx`;
    const module = { exports: {} as { default: () => unknown } };
    let draft: any;
    const updates: unknown[] = [];
    const source = ts.transpileModule(readFileSync(file, "utf8"), {
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    runInNewContext(source, { module, exports: module.exports, require(importName: string) {
      if (importName === "react") return {
        useState: (initial: unknown) => [initial, (next: unknown) => updates.push(next)],
        useEffect() {}, useRef: () => ({ current: null }),
      };
      if (importName === "react/jsx-runtime") return { jsx: (type: unknown, props: unknown) => ({ type, props }), jsxs: (type: unknown, props: unknown) => ({ type, props }) };
      if (importName === "react-router-dom") return { useParams: () => ({}), useNavigate: () => () => {} };
      if (importName === "@tanstack/react-query") return { useQuery: () => ({ isLoading: false }), useMutation: () => ({}), useQueryClient: () => ({}) };
      if (importName.endsWith("useUctGuard")) return { useUctGuard: () => ({ uct: { id: 1 } }) };
      if (importName.endsWith("AuthContext")) return { useAuth: () => ({ user: { id: 1 } }) };
      if (importName.endsWith("useTransferencias")) return { useTiposContrato: () => ({ tipos: [] }) };
      if (importName.endsWith("useFormDraft")) return { useFormDraft: (options: unknown) => { draft = options; return {}; } };
      if (importName.endsWith("equipamientoValidation")) return { getLocalIsoDate: () => "2026-11-04" };
      if (importName.endsWith("dateTime")) return { parseCivilDate: () => undefined };
      return { default: "stub" };
    } });
    module.exports.default();
    assert.equal(draft.hasContent(draft.value), false);
    const isEquipment = name === "Equipamiento";
    const usd = isEquipment ? { ...draft.value, moneda: "USD" } : { ...draft.value, data: { ...draft.value.data, moneda: "USD" } };
    assert.equal(draft.hasContent(usd), true);
    const legacy = isEquipment ? { ...draft.value } : { ...draft.value, data: { ...draft.value.data } };
    delete (isEquipment ? legacy : legacy.data).moneda;
    draft.onRestore(legacy);
    assert.equal((updates[0] as { moneda: string }).moneda, "ARS");
  });
}
