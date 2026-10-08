export const PROYECTO_CODIGO_MAX_LENGTH = 50;

function addMonths(date: Date, months: number): Date {
  const year = date.getFullYear();
  const month = date.getMonth() + months;
  const first = new Date(year, month, 1);
  return new Date(first.getFullYear(), first.getMonth(), Math.min(date.getDate(), new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate()));
}

export function validateDuracionProyecto(start: Date | null, end: Date | null): string | null {
  if (!start) return null;
  if (!end) return "Debe seleccionar una fecha de fin para definir una duración de 12 a 36 meses.";
  const inclusiveEnd = (months: number) => {
    const anniversary = addMonths(start, months);
    if (anniversary.getDate() < start.getDate()) return anniversary;
    anniversary.setDate(anniversary.getDate() - 1);
    return anniversary;
  };
  const min = inclusiveEnd(12);
  const max = inclusiveEnd(36);
  return end < min || end > max ? "La duración inicial debe ser de 12 a 36 meses inclusive." : null;
}

const PROYECTO_CODIGO_PATTERN = /^[A-Za-z0-9]+$/;

export function validateCodigoProyecto(value: string): string | null {
  const codigo = value.trim();

  if (!codigo) {
    return "Debe ingresar el código del proyecto";
  }

  if (codigo.length > PROYECTO_CODIGO_MAX_LENGTH) {
    return `El código no puede superar los ${PROYECTO_CODIGO_MAX_LENGTH} caracteres`;
  }

  if (!PROYECTO_CODIGO_PATTERN.test(codigo)) {
    return "El código solo puede contener letras y números";
  }

  return null;
}
