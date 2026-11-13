import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
function harness(file: string, values: any[], initialData?: any) {
  const h = {values: [...values], cursor: 0, calls: [] as any[], navigations: [] as any[], draft: null as any};
  const module = {exports: {} as any};
  const code = ts.transpileModule(readFileSync(`src/modules/${file}`, "utf8"), {compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  }}).outputText;
  const load = (path: string): any => {
    const result = {exports: {}};
    runInNewContext(ts.transpileModule(readFileSync(path, "utf8"), {compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS}}).outputText,
      {module: result, exports: result.exports, require});
    return result.exports;
  };
  const save = async (...args: any[]) => {h.calls.push(args); return {id: 1};};
  runInNewContext(code, {module, exports: module.exports, require: (name: string) => {
    if (name === "react") return {default: {}, useEffect() {}, useRef: () => ({current: null}),
      useState: (initial: unknown) => {const i = h.cursor++; if (!(i in h.values)) h.values[i] = initial;
        return [h.values[i], (next: any) => {h.values[i] = typeof next === "function" ? next(h.values[i]) : next;}];}};
    if (name === "react/jsx-runtime") return {jsx: (type: unknown, props: unknown) => ({type, props}), jsxs: (type: unknown, props: unknown) => ({type, props})};
    if (name === "react-router-dom") return {useParams: () => initialData ? {id: "1"} : {}, useNavigate: () => (...args: any[]) => h.navigations.push(args)};
    if (name === "@tanstack/react-query") return {
      useQuery: () => ({data: initialData, isLoading: false}), useQueryClient: () => ({invalidateQueries: async () => {}}),
      useMutation: (config: any) => {const execute = async (payload: any) => {const saved = await config.mutationFn(payload); await config.onSuccess?.(saved); return saved;};
        return {isPending: false, mutate: execute, mutateAsync: execute};},
    };
    if (name.includes("Services") || name.endsWith("transferenciasServices")) return {
      crearActividadDocencia: save, actualizarActividadDocencia: save,
      createEquipamiento: save, updateEquipamiento: save, createTransferencia: save, updateTransferencia: save,
    };
    if (name.endsWith("useUctGuard")) return {useUctGuard: () => ({uct: {id: 1}})};
    if (name.endsWith("AuthContext")) return {useAuth: () => ({user: {id: 1}})};
    if (name.endsWith("useTiposContrato") || name.endsWith("useTransferencias")) return {useTiposContrato: () => ({tipos: [{id: 1, nombre: "Convenio"}]})};
    if (name.endsWith("useInvestigadores")) return {useInvestigadores: () => ({data: []})};
    if (name.endsWith("useGradoAcademico")) return {useGradosAcademicos: () => ({data: []})};
    if (name.endsWith("useActividadDocenciaRol")) return {useRolesActividadDocencia: () => ({data: []})};
    if (name.endsWith("useFormDraft")) return {useFormDraft: (options: any) => {h.draft = options; return {clearDraft() {}, blocker: {state: "unblocked"}};}};
    if (name === "../../../lib/textValidation") return load("src/lib/textValidation.ts");
    if (name === "@/utils/dateTime") return load("src/utils/dateTime.ts");
    if (name === "@/utils/money") return load("src/utils/money.ts");
    if (name === "@/lib/liveValidation") return load("src/lib/liveValidation.ts");
    if (name.endsWith("equipamientoValidation")) return load("src/modules/recursos/utils/equipamientoValidation.ts");
    if (name === "@/lib/httpError") return {getErrorMessage: () => "Error", applyFieldErrors: () => false};
    return {default: "stub"};
  }});
  const walk = (node: any): any[] => !node ? [] : Array.isArray(node) ? node.flatMap(walk)
    : node.props ? [node, ...walk(node.props.children)] : [];
  const render = () => {h.cursor = 0; return walk(module.exports.default());};
  const submit = async () => {await render().find(node => node.type === "form").props.onSubmit({preventDefault() {}});};
  return {h, render, submit};
}

test("Docencia guarda fin abierto, elimina solo fecha_fin y evita PUT sin cambios", async () => {
  const values = [1, "Curso", "UTN", new Date(2026, 0, 1), null, 1, 1, {}, false, ""];
  const create = harness("produccion/pages/DocenciaForm.tsx", values);
  assert.equal(create.render().find(node => node.props.name === "fechaFin").props.required, undefined);
  await create.submit();
  assert.equal(create.h.calls[0][0].fecha_fin, null);
  const initial = {id: 1, investigador_id: 1, curso: "Curso", institucion: "UTN", fecha_inicio: "2026-01-01", fecha_fin: "2026-12-01", grado_academico_id: 1, rol_actividad_id: 1};
  const edit = harness("produccion/pages/DocenciaForm.tsx", values, initial);
  await edit.submit();
  assert.deepEqual(JSON.parse(JSON.stringify(edit.h.calls[0][1])), {fecha_fin: null});
  const unchanged = harness("produccion/pages/DocenciaForm.tsx", values, {...initial, fecha_fin: null});
  await unchanged.submit();
  assert.equal(unchanged.h.calls.length, 0);
  const invalid = harness("produccion/pages/DocenciaForm.tsx", [...values.slice(0, 4), new Date(2025, 11, 31), ...values.slice(5)]);
  await invalid.submit();
  assert.equal(invalid.h.calls.length, 0);
});

for (const equipment of [true, false]) {
  test(`${equipment ? "Equipamiento" : "Transferencias"}: cero válido, negativos y vacío rechazados`, async () => {
    const file = equipment ? "recursos/pages/EquipamientoForm.tsx" : "transferencia/pages/TransferenciasForm.tsx";
    const data = equipment
      ? {denominacion: "Equipo", descripcion_breve: "Descripción", fecha_incorporacion: "2026-01-01", monto_invertido: 0, moneda: "USD"}
      : {denominacion: "Convenio", demandante: "Universidad", descripcionActividad: "Actividad institucional", monto: "0", moneda: "USD", fechaInicio: "2026-01-01", fechaFin: "", tipoContratoId: "1"};
    const field = equipment ? "monto_invertido" : "monto";
    for (const amount of equipment ? [0, 10.50, -1, undefined] : ["0", "10.50", "-1", ""]) {
      const values = equipment ? [{...data, [field]: amount}, {}, false, ""] : [{...data, [field]: amount}, [], {}, false, ""];
      const form = harness(file, values);
      await form.submit();
      const valid = amount === 0 || amount === "0" || amount === 10.50 || amount === "10.50";
      assert.equal(form.h.calls.length, valid ? 1 : 0);
      if (valid) {
        assert.equal(form.h.calls[0][0][field], Number(amount));
        assert.equal(form.h.calls[0][0].moneda, "USD");
      }
    }
    const initial = equipment ? {id: 1, grupo_utn_id: 1, ...data} : {id: 1, grupoUtnId: 1, ...data, monto: 0, fechaFin: undefined, tipoContratoId: 1, adoptantes: []};
    const unchanged = harness(file, equipment ? [data, {}, false, ""] : [data, [], {}, false, ""], initial);
    await unchanged.submit();
    assert.equal(unchanged.h.calls.length, 0);
    if (equipment) assert.equal(unchanged.h.draft.hasContent({...data, denominacion: "", descripcion_breve: "", fecha_incorporacion: "", moneda: "ARS"}), true);
  });
}
