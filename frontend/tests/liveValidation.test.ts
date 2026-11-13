import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";
import { updateLiveValidationErrors } from "../src/lib/liveValidation.ts";
import { hasLetter, hasOnlyLettersAndSpaces } from "../src/lib/textValidation.ts";
import { getLocalIsoDate, validateFechaIncorporacion } from "../src/modules/recursos/utils/equipamientoValidation.ts";

test("la validación conserva errores ajenos y actualiza dependencias sin mutar el estado", () => {
  const previous = { titulo: "Error del servidor", fin: "Rango inválido", otro: "Otro error" };
  const next = updateLiveValidationErrors(previous, { fin: "Rango inválido" }, { titulo: "Título corto" }, "titulo");
  assert.deepEqual(next, { titulo: "Título corto", otro: "Otro error" });
  assert.equal(previous.fin, "Rango inválido");
  assert.deepEqual(updateLiveValidationErrors(previous, {}, {}, "fin"), { titulo: "Error del servidor", otro: "Otro error" });
});

// Ejecuta las mismas comprobaciones y callbacks del formulario, sin React ni API.
function formValidation(file: string, values: Record<string, unknown>) {
  const source = readFileSync(`src/modules/${file}`, "utf8");
  const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const declarations: string[] = [];
  const handlers: Record<string, string> = {};
  const setters: Record<string, string> = {};
  function visit(node: ts.Node) {
    if (ts.isFunctionDeclaration(node) && node.name && ["isValidEmail", "isValidUsername"].includes(node.name.text))
      declarations.push(node.getText(ast));
    if (ts.isVariableDeclaration(node)) {
      if (ts.isIdentifier(node.name) && ["validationValues", "getValidationErrors", "validateChangedField"].includes(node.name.text))
        declarations.push(`const ${node.getText(ast)};`);
      if (ts.isArrayBindingPattern(node.name) && node.initializer && ts.isCallExpression(node.initializer) && node.initializer.expression.getText(ast) === "useState") {
        const [value, setter] = node.name.elements;
        if (value && setter && ts.isBindingElement(value) && ts.isBindingElement(setter)) setters[setter.name.getText(ast)] = value.name.getText(ast);
      }
    }
    if (ts.isJsxAttribute(node) && node.name.getText(ast) === "onChange" && node.initializer && ts.isJsxExpression(node.initializer) && node.initializer.expression) {
      const handler = node.initializer.expression.getText(ast);
      const field = /validateChangedField\("([^"]+)"/.exec(handler)?.[1];
      if (field) handlers[field] = handler;
    }
    ts.forEachChild(node, visit);
  }
  visit(ast);
  let errors: Record<string, string> = { independiente: "Error del servidor" };
  let writes = 0;
  const scope: Record<string, unknown> = {
    ...values, hasLetter, hasOnlyLettersAndSpaces, getLocalIsoDate, validateFechaIncorporacion,
    isMoneda: (value: unknown) => value === "ARS" || value === "USD",
    updateLiveValidationErrors,
    setErrors: (updater: (previous: Record<string, string>) => Record<string, string>) => { errors = updater(errors); },
  };
  for (const [setter, value] of Object.entries(setters)) if (setter !== "setErrors")
    scope[setter] = (next: unknown) => { scope[value] = typeof next === "function" ? next(scope[value]) : next; };
  // Cualquier intento accidental de persistir durante la interacción falla.
  scope.mutation = { mutate: () => { writes++; }, mutateAsync: () => { writes++; } };
  const script = `${declarations.join("\n")}\nreturn { getValidationErrors, validateChangedField, handlers: {${Object.entries(handlers).map(([key, value]) => `${JSON.stringify(key)}: ${value}`).join(",")}} };`;
  const js = ts.transpileModule(script, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;
  const render = () => new Function(...Object.keys(scope), js)(...Object.values(scope));
  return { render, get errors() { return errors; }, get writes() { return writes; } };
}

test("Visitas valida durante la escritura y no oculta errores ajenos", () => {
  const form = formValidation("grupo/pages/VisitantesForm.tsx", { razon: "Visita académica", fecha: new Date(2026, 0, 1), procedencia: "Universidad", tipoVisitaId: 1 });
  form.render().handlers.procedencia({ target: { value: "1234" } });
  assert.match(form.errors.procedencia, /numerica/);
  assert.equal(form.errors.independiente, "Error del servidor");
  form.render().handlers.procedencia({ target: { value: "Universidad" } });
  assert.equal(form.errors.procedencia, undefined);
  assert.equal(form.writes, 0);
});

test("Docencia revalida el fin cuando cambia el inicio del período", () => {
  const form = formValidation("produccion/pages/DocenciaForm.tsx", {
    investigadorId: 1, curso: "Curso", institucion: "UTN", fechaInicio: new Date(2026, 0, 1), fechaFin: new Date(2026, 1, 1), gradoAcademicoId: 1, rolActividadId: 1,
  });
  form.render().handlers.fechaInicio(new Date(2026, 2, 1));
  assert.match(form.errors.fechaFin, /anterior/);
  form.render().handlers.fechaInicio(new Date(2026, 0, 1));
  assert.equal(form.errors.fechaFin, undefined);
  assert.equal(form.writes, 0);
});

test("Transferencias mantiene el error hasta alcanzar la longitud mínima", () => {
  const form = formValidation("transferencia/pages/TransferenciasForm.tsx", {
    data: { denominacion: "Convenio", demandante: "Municipalidad", descripcionActividad: "Actividad institucional", monto: "20", moneda: "ARS", fechaInicio: "2026-01-01", fechaFin: "", tipoContratoId: "1" },
  });
  form.render().handlers.denominacion({ target: { value: "A" } });
  assert.ok(form.errors.denominacion);
  form.render().handlers.denominacion({ target: { value: "AB" } });
  assert.ok(form.errors.denominacion);
  form.render().handlers.denominacion({ target: { value: "Convenio" } });
  assert.equal(form.errors.denominacion, undefined);
  assert.equal(form.writes, 0);
});

test("Becas acumula todos los errores vigentes y respeta el máximo del nombre", () => {
  const form = formValidation("recursos/pages/BecasForm.tsx", { form: { nombre_beca: "", descripcion: "", fecha_alta_grupo: "", fuente_financiamiento_id: "" }, fuentes: [] });
  const errors = form.render().getValidationErrors();
  assert.ok(errors.nombre_beca && errors.fecha_alta_grupo);
  form.render().validateChangedField("nombre_beca", { form: { nombre_beca: "A".repeat(101), descripcion: "", fecha_alta_grupo: "", fuente_financiamiento_id: "" } });
  assert.match(form.errors.nombre_beca, /100/);
  assert.equal(form.writes, 0);
});

test("Equipamiento rechaza denominaciones numéricas durante la interacción", () => {
  const form = formValidation("recursos/pages/EquipamientoForm.tsx", {
    data: { denominacion: "Equipo", descripcion_breve: "Descripción", monto_invertido: 100, moneda: "ARS", fecha_incorporacion: "2026-01-01" },
  });
  form.render().handlers.denominacion({ target: { value: "123" } });
  assert.match(form.errors.denominacion, /letras/);
  form.render().handlers.denominacion({ target: { value: "Equipo" } });
  assert.equal(form.errors.denominacion, undefined);
  assert.equal(form.writes, 0);
});

test("Contraseñas revalida la confirmación al modificar la nueva contraseña", () => {
  const form = formValidation("auth/pages/CambiarPassword.tsx", {
    passwordActual: "Anterior", passwordNueva: "Nueva123", passwordConfirmacion: "Nueva123", esPrimerLogin: false,
  });
  form.render().handlers.passwordNueva({ target: { value: "Nueva456" } });
  assert.match(form.errors.passwordConfirmacion, /coincidir/);
  form.render().handlers.passwordConfirmacion({ target: { value: "Nueva456" } });
  assert.equal(form.errors.passwordConfirmacion, undefined);
  form.render().handlers.passwordNueva({ target: { value: "abc" } });
  assert.match(form.errors.passwordNueva, /6/);
  assert.equal(form.writes, 0);
});

test("Acceso muestra ambos obligatorios sin imponer reglas nuevas a credenciales existentes", () => {
  const form = formValidation("auth/pages/Login.tsx", { usuario: "", password: "" });
  assert.deepEqual(Object.keys(form.render().getValidationErrors()), ["usuario", "password"]);
  form.render().handlers.usuario({ target: { value: "usuario.existente" } });
  form.render().handlers.password({ target: { value: "clave" } });
  assert.equal(form.errors.password, undefined);
  assert.equal(form.writes, 0);
});

test("Movimientos retira el error de cotización al llegar la respuesta y conserva errores del servidor", () => {
  const source = readFileSync("src/modules/recursos/pages/ErogacionesForm.tsx", "utf8");
  const ast = ts.createSourceFile("ErogacionesForm.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let effect = "";
  function visit(node: ts.Node) {
    if (ts.isCallExpression(node) && node.expression.getText(ast) === "useEffect" && node.arguments[0]?.getText(ast).includes("previous.moneda"))
      effect = node.arguments[0].getText(ast);
    ts.forEachChild(node, visit);
  }
  visit(ast);
  assert.ok(effect);
  const message = "No existe una cotización oficial disponible. Seleccione otra fecha o reintente.";
  let errors: Record<string, string> = { moneda: message, monto: "Revise el monto" };
  const applyEffect = new Function("cotizacion", "data", "setErrors", "updateLiveValidationErrors", `return (${effect})();`);
  const setErrors = (update: (previous: typeof errors) => typeof errors) => { errors = update(errors); };
  applyEffect(null, { moneda: "USD" }, setErrors, updateLiveValidationErrors);
  assert.equal(errors.moneda, message);
  applyEffect({ valor: "1200" }, { moneda: "USD" }, setErrors, updateLiveValidationErrors);
  assert.deepEqual(errors, { monto: "Revise el monto" });
  errors.moneda = "Error específico del servidor";
  applyEffect({ valor: "1200" }, { moneda: "USD" }, setErrors, updateLiveValidationErrors);
  assert.equal(errors.moneda, "Error específico del servidor");
});
