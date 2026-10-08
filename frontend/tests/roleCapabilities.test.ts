import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { getRoleCapabilities } from "../src/modules/auth/utils/roleCapabilities.ts";

const profileSource = readFileSync(
  new URL("../src/modules/auth/pages/MiPerfil.tsx", import.meta.url),
  "utf8"
);

test("el lector conoce que su sesion no admite mutaciones", () => {
  const capabilities = getRoleCapabilities("LECTURA");

  assert.equal(capabilities.label, "Lector");
  assert.equal(capabilities.summary, "Su sesión es de solo lectura.");
  assert.ok(
    capabilities.restricted.includes(
      "No puede agregar, editar ni eliminar registros."
    )
  );
});

test("el gestor conoce sus permisos y la restriccion de usuarios", () => {
  const capabilities = getRoleCapabilities("GESTOR");

  assert.ok(
    capabilities.allowed.includes(
      "Consultar, agregar, editar y eliminar registros."
    )
  );
  assert.ok(
    capabilities.restricted.includes(
      "No puede administrar usuarios ni modificar sus roles."
    )
  );
});

test("el administrador conoce sus capacidades generales", () => {
  const capabilities = getRoleCapabilities("ADMIN");

  assert.equal(capabilities.label, "Administrador");
  assert.ok(capabilities.allowed.some((item) => item.includes("Administrar usuarios")));
});

test("el perfil presenta solo las capacidades disponibles del rol activo", () => {
  assert.match(profileSource, /getRoleCapabilities\(user\.rol\)/);
  assert.match(profileSource, /Permisos de la sesión/);
  assert.match(profileSource, /Acciones disponibles/);
  assert.match(profileSource, /roleCapabilities\.allowed\.map/);
  assert.doesNotMatch(profileSource, /roleCapabilities\.restricted\.map/);
});
