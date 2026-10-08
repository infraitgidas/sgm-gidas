function centavos(value: string): bigint {
  const [entero, decimales = ""] = value.split(".");
  return BigInt(entero) * 100n + BigInt(decimales.padEnd(2, "0"));
}

export function excedeSaldoDisponible(monto: string, saldoDisponible: string, montoAnterior = "0.00"): boolean {
  return centavos(monto) > centavos(saldoDisponible) + centavos(montoAnterior);
}

export function equivalenteArs(montoUsd: string, cotizacion: string): string {
  const [entero, fraccion = ""] = cotizacion.split(".");
  if (!/^\d+$/.test(entero) || !/^\d{0,6}$/.test(fraccion)) throw new Error("Cotización inválida");
  const tasa = BigInt(entero) * 1_000_000n + BigInt(fraccion.padEnd(6, "0"));
  const resultado = (centavos(montoUsd) * tasa + 500_000n) / 1_000_000n;
  return `${resultado / 100n}.${String(resultado % 100n).padStart(2, "0")}`;
}
