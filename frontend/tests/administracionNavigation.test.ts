import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import * as catalogNavigation from "../src/modules/catalogos/utils/catalogNavigation.ts";

const mainSource = await readFile(new URL("../src/main.tsx", import.meta.url), "utf8");
const sidebarSource = await readFile(new URL("../src/components/Sidebar.tsx", import.meta.url), "utf8");
const layoutSource = await readFile(new URL("../src/layouts/AppLayout.tsx", import.meta.url), "utf8");
const pageSource = await readFile(
  new URL("../src/modules/administracion/pages/AdministracionHome.tsx", import.meta.url),
  "utf8"
);
const usersHomeSource = await readFile(new URL("../src/modules/auth/pages/UsuariosHome.tsx", import.meta.url), "utf8");
const usersFormSource = await readFile(new URL("../src/modules/auth/pages/UsuariosForm.tsx", import.meta.url), "utf8");

test("protege el panel de administracion para ADMIN", () => {
  assert.match(mainSource, /path: "administracion"[\s\S]*?<ProtectedRoute requiredRole="ADMIN">/);
  assert.match(mainSource, /lazy\(\(\) => import\("@\/modules\/administracion\/pages\/AdministracionHome"\)\)/);
});

test("ADMIN conserva Inicio, Administración, Memorias y Búsqueda sin consultar el estado de memorias", () => {
  const require = createRequire(import.meta.url);
  for (const rol of ["ADMIN", "GESTOR", "LECTURA"]) {
    const module = { exports: {} as { default: () => any } };
    const code = ts.transpileModule(sidebarSource, { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
    } }).outputText;
    runInNewContext(code, { module, exports: module.exports, require: (name: string) => {
      if (name === "@/context/AuthContext") return { useAuth: () => ({
        user: { rol }, isAdmin: () => rol === "ADMIN", isGestor: () => rol === "GESTOR",
        logout: async () => {},
      }) };
      if (name === "react-router-dom") return {
        useLocation: () => ({ pathname: "/inicio", search: "", hash: "", state: null }),
        NavLink: ({ to, children }: any) => createElement("a", { href: to }, children),
      };
      if (name === "@/modules/catalogos/utils/catalogNavigation") return catalogNavigation;
      // Cualquier dependencia de consultas o estados de memorias falla aquí.
      if (name.startsWith("@/")) throw new Error(`Dependencia inesperada: ${name}`);
      return require(name);
    } });
    const html = renderToStaticMarkup(createElement(module.exports.default));
    for (const route of ["inicio", "memorias", "busqueda"]) {
      assert.ok(html.includes(`href="/${route}"`), `${rol}: falta ${route}`);
    }
    for (const route of ["personal", "proyectos", "trabajos-reunion", "equipamiento", "movimientos", "documentacion", "transferencias"]) {
      assert.equal(html.includes(`href="/${route}"`), rol !== "ADMIN", `${rol}: acceso ${route}`);
    }
    if (rol === "ADMIN") {
      const destinations = [...html.matchAll(/href="([^"]+)"/g)].map((match) => match[1]);
      assert.deepEqual(destinations, ["/inicio", "/administracion", "/memorias", "/busqueda", "/mi-perfil", "/cambiar-password"]);
    }
    assert.equal(html.includes('href="/administracion"'), rol === "ADMIN");
    assert.equal(html.includes('href="/catalogos"'), rol === "GESTOR");
    assert.equal(html.includes('href="/informes/uct"'), rol === "GESTOR");
  }
});

test("ubica las acciones de usuario en el pie del menu lateral", () => {
  assert.match(sidebarSource, /user\?\.nombre_usuario/);
  assert.match(sidebarSource, /user\?\.mail/);
  assert.match(sidebarSource, /Mi perfil/);
  assert.match(sidebarSource, /Cambiar contraseña/);
  assert.match(sidebarSource, /Cerrar sesión/);
  assert.match(sidebarSource, /await logout\(\)/);
});

test("despliega las opciones del perfil desde el icono superior", () => {
  assert.match(layoutSource, /aria-label="Abrir opciones del perfil"/);
  assert.match(layoutSource, /aria-expanded=\{isProfileOpen\}/);
  assert.match(layoutSource, /Mi perfil/);
  assert.match(layoutSource, /Cambiar contraseña/);
  assert.match(layoutSource, /Cerrar sesión/);
  assert.match(layoutSource, /closeOnOutsideClick/);
  assert.match(layoutSource, /event\.key === "Escape"/);
  assert.match(layoutSource, /await logout\(\)/);
});

test("presenta informacion accionable sin un contrato backend nuevo", () => {
  assert.match(pageSource, /getUsuarios/);
  assert.match(pageSource, /useUct/);
  assert.match(pageSource, /useDirectivos/);
  assert.match(pageSource, /Atención requerida/);
  assert.match(pageSource, /Próxima etapa/);
  assert.doesNotMatch(pageSource, /\/api\/v1\/administracion\/resumen/);
});

test("ofrece una sola entrada para crear usuarios y retornos consistentes", () => {
  assert.match(pageSource, /title="Crear usuario"/);
  assert.match(pageSource, /to="\/usuarios\/nuevo"/);
  assert.doesNotMatch(usersHomeSource, /Nuevo Usuario|\/usuarios\/nuevo/);
  assert.match(usersHomeSource, /Volver a Administración/);
  assert.match(usersFormSource, /nav\("\/administracion"\)/);
  assert.match(pageSource, /onClick=\{\(\) => navigate\(-1\)\}/);
});
