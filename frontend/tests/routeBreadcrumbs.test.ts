import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { getRouteBreadcrumbs } from "../src/modules/shared/utils/routeBreadcrumbs.ts";

test("resuelve detalle y edición de Personal con enlaces a rutas reales", () => {
  assert.deepEqual(getRouteBreadcrumbs("/personal/investigador/42"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Personal", to: "/personal" },
    { label: "Detalle" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/personal/investigador/42/editar"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Personal", to: "/personal" },
    { label: "Detalle", to: "/personal/investigador/42" },
    { label: "Editar" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/becarios/7/editar")[2], {
    label: "Detalle",
    to: "/becarios/7",
  });
});

test("resuelve rutas de edición de los módulos y el alias anterior de Proyectos", () => {
  assert.deepEqual(getRouteBreadcrumbs("/trabajos-reunion/8/editar"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Trabajos en Reunión Científica", to: "/trabajos-reunion" },
    { label: "Detalle", to: "/trabajos-reunion/8" },
    { label: "Editar" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/proyectos/5/editar")[2], {
    label: "Detalle",
    to: "/proyectos/5",
  });
  assert.deepEqual(getRouteBreadcrumbs("/proyectos/editar/5")[2], {
    label: "Detalle",
    to: "/proyectos/5",
  });
});

test("versiones de Memorias omite el segmento sin página y oculta los identificadores", () => {
  assert.deepEqual(getRouteBreadcrumbs("/memorias/3/versiones/12"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Memorias", to: "/memorias" },
    { label: "Detalle", to: "/memorias/3" },
    { label: "Versión" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/memorias/3"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Memorias", to: "/memorias" },
    { label: "Detalle" },
  ]);
});

test("incluye rutas de primer nivel, altas, acceso público y página inexistente", () => {
  assert.deepEqual(getRouteBreadcrumbs("/inicio"), [{ label: "Inicio" }]);
  assert.deepEqual(getRouteBreadcrumbs("/personal"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Personal" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/usuarios/nuevo"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Usuarios", to: "/usuarios" },
    { label: "Nuevo" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/uct/nueva"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Nueva UCT" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/uct/editar"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Editar UCT" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/login"), [
    { label: "Portada", to: "/" },
    { label: "Iniciar sesión" },
  ]);
  assert.deepEqual(getRouteBreadcrumbs("/ruta-inexistente"), [
    { label: "Inicio", to: "/inicio" },
    { label: "Página no encontrada" },
  ]);
});

test("cubre todas las rutas actuales del router sin exponer IDs en etiquetas", () => {
  const router = readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
  const paths = [...router.matchAll(/path:\s*"([^"]+)"/g)]
    .map((match) => match[1])
    .filter((path) => path !== "*");

  assert.ok(paths.length > 0);
  for (const path of paths) {
    const concretePath = path.startsWith("/") ? path : `/${path.replace(":rol", "investigador").replace(/:id|:versionId/g, "42")}`;
    const items = getRouteBreadcrumbs(concretePath);
    assert.ok(items.length >= 1, `Falta breadcrumb para ${path}`);
    assert.equal(items.at(-1)?.to, undefined, `El destino actual de ${path} debe ser texto`);
    assert.ok(items.every((item) => !/\d/.test(item.label)), `El breadcrumb de ${path} expone un ID`);
  }
});
