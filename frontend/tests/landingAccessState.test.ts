import assert from "node:assert/strict";
import test from "node:test";
import { getLandingAccessState } from "../src/modules/auth/utils/landingAccessState.ts";

const initialState = {
  sessionLoading: false,
  userExists: false,
  setupError: false,
  needsInitialAdmin: undefined,
};

test("muestra carga mientras se restaura la sesion", () => {
  assert.equal(
    getLandingAccessState({
      ...initialState,
      sessionLoading: true,
    }),
    "loading"
  );
});

test("prioriza una sesion autenticada sobre la consulta de configuracion", () => {
  assert.equal(
    getLandingAccessState({
      ...initialState,
      userExists: true,
      setupError: true,
    }),
    "authenticated"
  );
});

test("muestra carga mientras la configuracion inicial sigue indeterminada", () => {
  assert.equal(getLandingAccessState(initialState), "loading");
});

test("muestra un error cuando la consulta inicial falla sin datos", () => {
  assert.equal(
    getLandingAccessState({
      ...initialState,
      setupError: true,
    }),
    "error"
  );
});

test("dirige al registro cuando falta el administrador inicial", () => {
  assert.equal(
    getLandingAccessState({
      ...initialState,
      needsInitialAdmin: true,
    }),
    "first-admin"
  );
});

test("dirige al login cuando el sistema ya esta configurado", () => {
  assert.equal(
    getLandingAccessState({
      ...initialState,
      needsInitialAdmin: false,
    }),
    "login"
  );
});

test("conserva el registro cuando existe un dato cacheado durante un refetch", () => {
  assert.equal(
    getLandingAccessState({
      ...initialState,
      setupError: true,
      needsInitialAdmin: true,
    }),
    "first-admin"
  );
});

test("conserva el login si un refetch falla pero existe un dato cacheado", () => {
  assert.equal(
    getLandingAccessState({
      ...initialState,
      setupError: true,
      needsInitialAdmin: false,
    }),
    "login"
  );
});
