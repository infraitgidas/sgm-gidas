import assert from "node:assert/strict";
import test from "node:test";

import { validateDuracionProyecto } from "../src/modules/proyectos/utils/proyectoValidation.ts";
import { formatProyectoRelationHistoryEntry } from "../src/modules/proyectos/utils/proyectoHistory.ts";

const fecha = (value: string) => new Date(`${value}T00:00:00`);

test("duración inicial inclusiva admite 12 y 36 meses y rechaza los límites exteriores", () => {
  const inicio = fecha("2024-01-01");
  assert.equal(validateDuracionProyecto(inicio, fecha("2024-12-31")), null);
  assert.equal(validateDuracionProyecto(inicio, fecha("2026-12-31")), null);
  assert.match(validateDuracionProyecto(inicio, fecha("2024-12-30")) ?? "", /12 a 36/);
  assert.match(validateDuracionProyecto(inicio, fecha("2027-01-01")) ?? "", /12 a 36/);
  assert.match(validateDuracionProyecto(inicio, null) ?? "", /fecha de fin/);
  assert.equal(validateDuracionProyecto(fecha("2024-02-29"), fecha("2025-02-28")), null);
});

test("el historial describe la decisión de prórroga", () => {
  assert.deepEqual(formatProyectoRelationHistoryEntry({
    id: 1, campo: "prorroga", valor_nuevo: { fecha_fin: "2027-12-31", motivo: "Extensión para completar resultados" },
  }), {
    title: "Prórroga de 12 meses",
    description: "Nuevo fin: 31/12/2027. Justificación: Extensión para completar resultados",
  });
});
