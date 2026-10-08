import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";
import { transformSync } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { applyFieldErrors, focusFieldErrors, getApiErrorMessage, getApiFieldErrors, getErrorMessage, mapFieldErrors } from "../src/lib/httpError.ts";

test("la interfaz no compone referencias internas en mensajes visibles", () => {
  const visit = (directory: string): void => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) { visit(path); continue; }
      if (!/\.(?:ts|tsx)$/.test(entry.name)) continue;
      const source = readFileSync(path, "utf8");
      assert.doesNotMatch(source, /includeTrackingReference/i, path);
      if (entry.name !== "httpError.ts") assert.doesNotMatch(source, /Referencia de seguimiento/i, path);
      assert.doesNotMatch(source, /(?:`[^`]*\$\{\s*(?:requestId|request_id)\s*\}[^`]*`|\+\s*(?:requestId|request_id)\b|\b(?:requestId|request_id)\s*\+)/, path);
    }
  };
  visit(fileURLToPath(new URL("../src", import.meta.url)));
});

test("Field muestra el error junto al control sin duplicar el mensaje heredado", () => {
  const source = readFileSync(new URL("../src/components/Field.tsx", import.meta.url), "utf8");
  const compiled = transformSync(source, { loader: "tsx", format: "cjs", jsx: "automatic" }).code;
  const module = { exports: {} as { default: React.ComponentType<Record<string, unknown>> } };
  runInNewContext(compiled, { module, exports: module.exports, require: createRequire(import.meta.url) });
  const Field = module.exports.default;
  const error = "Use letras y números.";
  const control = createElement("input", { name: "codigoProyecto" });
  const markup = renderToStaticMarkup(createElement(Field, { label: "Código", name: "codigoProyecto", error }, control));
  assert.match(markup, /data-error-field="codigoProyecto"/);
  assert.match(markup, /role="alert"/);
  assert.ok(markup.indexOf("<input") < markup.indexOf(error));
  const legacy = renderToStaticMarkup(createElement(Field, { label: "Código", name: "codigoProyecto", error },
    control, createElement("p", {}, error)));
  assert.equal(legacy.split(error).length - 1, 1);
  const initial = renderToStaticMarkup(createElement(Field, { label: "Código", name: "codigoProyecto" }, control));
  assert.doesNotMatch(initial, /role="alert"|border-rose-500/);
});

test("mapea campos y conserva los errores desconocidos", () => {
  const error = { body: { error: { details: { fields: {
    codigo_proyecto: "Use letras y números.",
    id_investigador: "Seleccione un investigador disponible.",
    campo_futuro: "Revise la selección.",
  } } } } };
  assert.deepEqual(mapFieldErrors(error, ["codigoProyecto", "investigadoresIds"]), {
    codigoProyecto: "Use letras y números.", investigadoresIds: "Seleccione un investigador disponible.",
  });
  assert.equal(Object.keys(getApiFieldErrors(error)).length, 3);
  assert.deepEqual(mapFieldErrors({ body: { fields: { mail: "Revise el correo." } } }, ["email"]), { email: "Revise el correo." });
});

test("asocia validaciones de visitas y participaciones por clave HTTP", () => {
  const visita = { body: { error: { details: { fields: {
    tipo_visita_id: "Seleccione un tipo de visita disponible.",
    procedencia: "Ingrese una procedencia con letras.",
  } } } } };
  assert.deepEqual(mapFieldErrors(visita, ["razon", "procedencia", "tipoVisita"]), {
    tipoVisita: "Seleccione un tipo de visita disponible.",
    procedencia: "Ingrese una procedencia con letras.",
  });

  const participacion = { body: { error: { details: { fields: {
    investigador_id: "Seleccione un investigador disponible.",
    nombre_evento: "Ingrese el nombre del evento.",
    forma_participacion: "Ingrese la forma de participación.",
  } } } } };
  assert.deepEqual(mapFieldErrors(participacion, ["investigador", "nombreEvento", "formaParticipacion"]), {
    investigador: "Seleccione un investigador disponible.",
    nombreEvento: "Ingrese el nombre del evento.",
    formaParticipacion: "Ingrese la forma de participación.",
  });
});

test("mapea campos HTTP de UCT sin interpretar mensajes", () => {
  const error = { body: { error: { details: { fields: {
    nombre_unidad_academica: "Ingrese la facultad regional.",
    objetivo_desarrollo: "Ingrese los objetivos del grupo.",
  } } } } };
  assert.deepEqual(mapFieldErrors(error, ["facultadRegional", "objetivos"]), {
    facultadRegional: "Ingrese la facultad regional.",
    objetivos: "Ingrese los objetivos del grupo.",
  });
});

test("mapea campos de trabajos por clave HTTP", () => {
  const error = { body: { error: { details: { fields: {
    titulo_trabajo: "Ingrese el título del trabajo.",
    nombre_reunion: "Ingrese el nombre de la reunión.",
    tipo_reunion_id: "Seleccione un tipo disponible.",
    fecha_presentacion: "Ingrese una fecha válida.",
  } } } } };
  assert.deepEqual(mapFieldErrors(error, ["titulo", "nombreReunion", "tipoId", "fechaPresentacion"]), {
    titulo: "Ingrese el título del trabajo.",
    nombreReunion: "Ingrese el nombre de la reunión.",
    tipoId: "Seleccione un tipo disponible.",
    fechaPresentacion: "Ingrese una fecha válida.",
  });
});

test("descarta detalles técnicos y nunca muestra el identificador interno", () => {
  const fallback = "Intente nuevamente.";
  assert.equal(getErrorMessage({ body: { error: { message: "SELECT password FROM users", details: { request_id: "req-09" } } } }, fallback),
    fallback);
  assert.equal(getErrorMessage({ body: { requestId: "<script>" } }, fallback), fallback);
  assert.deepEqual(getApiFieldErrors({ body: { fields: { nombre: "SQLAlchemy column secret", mail: 123 } } }), {});
});

test("conserva el mensaje público sin reflejar metadata operativa", () => {
  const fallback = "Lo sentimos, no pudimos guardar los cambios. Intente nuevamente.";
  const error = {
    body: {
      error: {
        message: "Revise la fecha de presentación e intente nuevamente.",
        details: { request_id: "req-interno-17" },
      },
    },
  };

  assert.equal(
    getErrorMessage(error, fallback),
    "Revise la fecha de presentación e intente nuevamente.",
  );
  assert.equal(
    getErrorMessage(
      { body: { error: { message: "SELECT password FROM users", details: { request_id: "req-interno-17" } } } },
      fallback,
    ),
    fallback,
  );
  assert.equal(getErrorMessage({ body: { error: { message: "Referencia de seguimiento: req-interno-17" } } }, fallback), fallback);
  assert.equal(getErrorMessage({ body: { error: { message: "Error request_id=req-interno-17" } } }, fallback), fallback);
  assert.equal(getErrorMessage({ body: { error: { message: "Revise los datos.", details: { request_id: "<script>" } } } }, fallback), "Revise los datos.");
  assert.equal(getErrorMessage({ body: { error: { details: { request_id: { value: "secreto" } } } } }, fallback), fallback);
});

test("enfoca el primer campo inválido en el orden visual", () => {
  const previous = globalThis.requestAnimationFrame;
  const focused: string[] = [];
  globalThis.requestAnimationFrame = callback => { callback(0); return 0; };
  try {
    const root = { querySelectorAll: () => ["nombre", "codigoProyecto", "fechaFin"].map(name => ({
      dataset: { errorField: name }, querySelector: () => ({ focus: () => focused.push(name) }),
    })) } as unknown as ParentNode;
    focusFieldErrors({ fechaFin: "Revise la fecha.", codigoProyecto: "Use letras y números." }, root);
    assert.deepEqual(focused, ["codigoProyecto"]);
  } finally { globalThis.requestAnimationFrame = previous; }
});

test("un error sin control conocido conserva el aviso general", () => {
  let updated = false;
  assert.equal(applyFieldErrors({ body: { fields: { desconocido: "Revise el valor." } } },
    () => { updated = true; }, ["nombre"]), false);
  assert.equal(updated, false);
});

test("lee el mensaje del contrato tipado del backend", () => {
  assert.equal(
    getApiErrorMessage({
      data: null,
      error: { code: "VALIDATION_ERROR", message: "Revise los datos." },
    }),
    "Revise los datos."
  );
});

test("mantiene compatibilidad con contratos heredados", () => {
  assert.equal(getApiErrorMessage({ error: "Error heredado" }), "Error heredado");
  assert.equal(getApiErrorMessage({ message: "Mensaje heredado" }), "Mensaje heredado");
  assert.equal(getApiErrorMessage({ detail: "Detalle heredado" }), "Detalle heredado");
});

test("no refleja respuestas de texto o estructuras desconocidas", () => {
  assert.equal(getApiErrorMessage("SQL connection failed at internal-host"), null);
  assert.equal(getApiErrorMessage({ error: { details: { trace: "secret" } } }), null);
});

test("usa un fallback accionable cuando no existe un mensaje seguro", () => {
  const fallback = "Lo sentimos, no pudimos guardar los cambios. Intente nuevamente.";
  assert.equal(getErrorMessage({ body: "proxy failure" }, fallback), fallback);
  assert.equal(
    getErrorMessage({ body: { error: { message: "Conflicto de estado" } } }, fallback),
    "Conflicto de estado"
  );
});
