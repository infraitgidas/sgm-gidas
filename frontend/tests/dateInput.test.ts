import assert from "node:assert/strict";
import test from "node:test";
import { formatDateInput, replaceDateDigit } from "../src/utils/dateInput.ts";

test("agrega separadores al escribir una fecha desde cero", () => {
  assert.equal(formatDateInput("17092026"), "17/09/2026");
  assert.equal(formatDateInput("170"), "17/0");
  assert.equal(formatDateInput("01/022"), "01/02/2");
  assert.equal(formatDateInput("01/022022"), "01/02/2022");
  assert.equal(formatDateInput("01/02/2022"), "01/02/2022");
  let written = "";
  for (const digit of "01022022") written = formatDateInput(written + digit);
  assert.equal(written, "01/02/2022");
});

test("sobrescribe un dígito al posicionar el cursor en una fecha completa", () => {
  assert.deepEqual(replaceDateDigit("17/09/2026", 3, "1"), {
    value: "17/19/2026",
    cursor: 4,
  });
  assert.deepEqual(replaceDateDigit("17/09/2026", 2, "1"), {
    value: "17/19/2026",
    cursor: 4,
  });
  assert.deepEqual(replaceDateDigit("17/09/2026", 6, "3"), {
    value: "17/09/3026",
    cursor: 7,
  });
});

test("preserva los otros segmentos al reemplazar día, mes o año", () => {
  assert.equal(formatDateInput("1/09/2026"), "1/09/2026");
  assert.equal(formatDateInput("17/1/2026"), "17/1/2026");
  assert.equal(formatDateInput("17/09/203"), "17/09/203");
  assert.equal(formatDateInput("18/09/2026"), "18/09/2026");
  assert.equal(formatDateInput("17/10/2026"), "17/10/2026");
  assert.equal(formatDateInput("17/09/2027"), "17/09/2027");
});
