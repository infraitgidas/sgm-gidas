export function validateDni(value: string): string | null {
  return /^[0-9]{7,8}$/.test(value) ? null : "Ingrese un DNI de 7 u 8 dígitos, sin puntos.";
}

export function validateCuil(value: string, dni: string): string | null {
  const match = /^([0-9]{2})-([0-9]{8})-([0-9])$/.exec(value);
  if (!match) return "Ingrese el CUIL con formato XX-XXXXXXXX-X.";
  if (match[2] !== dni.padStart(8, "0")) return "El número central del CUIL debe coincidir con el DNI.";
  const weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  const digits = `${match[1]}${match[2]}`.split("").map(Number);
  const remainder = 11 - digits.reduce((sum, digit, index) => sum + digit * weights[index], 0) % 11;
  const expected = remainder === 11 ? 0 : remainder === 10 ? 9 : remainder;
  return Number(match[3]) === expected ? null : "El dígito verificador del CUIL no es válido.";
}
