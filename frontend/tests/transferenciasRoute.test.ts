import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

test("el listado de transferencias usa la ruta canónica sin redirección", async () => {
  const requests: string[] = [];
  const source = readFileSync("src/modules/transferencia/services/transferenciasServices.ts", "utf8");
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = { exports: {} as Record<string, (...args: unknown[]) => Promise<unknown>> };
  runInNewContext(code, {
    module,
    exports: module.exports,
    require: (path: string) => path === "@/lib/http"
      ? { http: async (url: string) => { requests.push(url); return []; } }
      : { isMockMode: () => false },
  });

  assert.deepEqual(await module.exports.getTransferencias("true"), []);
  assert.deepEqual(requests, ["/transferencias/?activos=true"]);
});

test("el alta recibe el número asignado por el servidor sin enviarlo", async () => {
  const requests: Array<{ url: string; body: Record<string, unknown> }> = [];
  const source = readFileSync("src/modules/transferencia/services/transferenciasServices.ts", "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} as Record<string, (...args: unknown[]) => Promise<unknown>> };
  runInNewContext(code, {
    module,
    exports: module.exports,
    require: (path: string) => path === "@/lib/http"
      ? { http: async (url: string, options: { body: string }) => {
          requests.push({ url, body: JSON.parse(options.body) });
          return { id: 3, numero_transferencia: 43, denominacion: "Convenio", demandante: "Municipalidad", descripcion_actividad: "Asistencia técnica", monto: 100, fecha_inicio: "2026-09-25", fecha_fin: null, tipo_contrato: "Convenio", grupo: "GIDAS", adoptantes: [{ id: 7, nombre: "Instituto Regional" }] };
        } }
      : { isMockMode: () => false },
  });
  const saved = await module.exports.createTransferencia({ denominacion: "Convenio", demandante: "Municipalidad", descripcionActividad: "Asistencia técnica", monto: 100, fechaInicio: "2026-09-25", tipoContratoId: 1, grupoUtnId: 1, adoptantesIds: [], adoptantesNuevos: ["Instituto Regional"] }) as { numeroTransferencia: number; adoptantes: Array<{ nombre: string }> };
  assert.equal(saved.numeroTransferencia, 43);
  assert.deepEqual(Array.from(saved.adoptantes, item => item.nombre), ["Instituto Regional"]);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "/transferencias");
  assert.equal("numero_transferencia" in requests[0].body, false);
  assert.deepEqual(requests[0].body.adoptantes_nuevos, ["Instituto Regional"]);
});
