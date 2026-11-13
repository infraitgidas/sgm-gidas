import assert from "node:assert/strict";
import test from "node:test";
import {
  formatFecha,
  formatFechaHora,
  getCivilYear,
  getInstitutionalMinDate,
  isInstitutionalDate,
  parseApiTimestamp,
  parseCivilDate,
  toCivilDateString,
} from "../src/utils/dateTime.ts";

process.env.TZ = "America/Argentina/Buenos_Aires";

test("mantiene una fecha civil de inicio de año en Argentina", () => {
  assert.equal(formatFecha("2026-01-01"), "01/01/2026");
  assert.equal(getCivilYear("2026-01-01"), 2026);
});

test("mantiene una fecha civil de fin de año en Argentina", () => {
  assert.equal(formatFecha("2026-12-31"), "31/12/2026");
  assert.equal(toCivilDateString(parseCivilDate("2026-12-31")), "2026-12-31");
});

test("rechaza fechas civiles inexistentes", () => {
  assert.equal(parseCivilDate("2026-02-31"), null);
  assert.equal(formatFecha("2026-02-31"), "—");
});

test("aplica el inicio del rango institucional en 2010", () => {
  assert.equal(toCivilDateString(getInstitutionalMinDate()), "2010-01-01");
  assert.equal(isInstitutionalDate("2009-12-31"), false);
  assert.equal(isInstitutionalDate("2010-01-01"), true);
});

test("interpreta timestamps sin zona del contrato heredado como UTC", () => {
  const parsed = parseApiTimestamp("2026-09-07T02:13:31");
  assert.equal(
    parsed?.toISOString(),
    "2026-09-07T02:13:31.000Z"
  );
  assert.equal(parsed?.getDate(), 6);
  assert.equal(parsed?.getHours(), 23);
  assert.equal(
    formatFechaHora("2026-09-07T02:13:31"),
    "6/9/2026, 23:13:31"
  );
});

test("respeta timestamps que ya incluyen una zona explícita", () => {
  assert.equal(
    parseApiTimestamp("2026-09-07T02:13:31-03:00")?.toISOString(),
    "2026-09-07T05:13:31.000Z"
  );
});

test("muestra horas argentinas de 24 horas independientemente de la zona del equipo", () => {
  const originalZone = process.env.TZ;
  try {
    for (const zone of ["UTC", "America/New_York", "Asia/Tokyo"]) {
      process.env.TZ = zone;
      for (const timestamp of [
        "2026-09-07T02:13:31",
        "2026-09-07T02:13:31Z",
        "2026-09-06T23:13:31-03:00",
      ]) {
        assert.equal(formatFechaHora(timestamp), "6/9/2026, 23:13:31");
      }
      assert.equal(formatFechaHora("2026-09-07T03:00:00Z"), "7/9/2026, 00:00:00");
      assert.equal(formatFechaHora("2026-09-07T16:00:00Z"), "7/9/2026, 13:00:00");
      assert.equal(formatFechaHora("2026-01-01T02:59:59Z"), "31/12/2025, 23:59:59");
    }
  } finally {
    if (originalZone === undefined) delete process.env.TZ;
    else process.env.TZ = originalZone;
  }
});

test("conserva los fallbacks de marcas ausentes o inválidas", () => {
  assert.equal(formatFechaHora(null), "-");
  assert.equal(formatFechaHora(undefined), "-");
  assert.equal(formatFechaHora(""), "-");
  assert.equal(formatFechaHora("inválida"), "-");
  assert.equal(formatFechaHora("inválida", "Sin fecha"), "Sin fecha");
});
