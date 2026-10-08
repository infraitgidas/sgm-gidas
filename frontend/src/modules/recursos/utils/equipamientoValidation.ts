export const EQUIPAMIENTO_MIN_FECHA_INCORPORACION = "2010-01-01";

function isIsoDate(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(year, month - 1, day);

  return (
    parsed.getFullYear() === year &&
    parsed.getMonth() === month - 1 &&
    parsed.getDate() === day
  );
}

export function getLocalIsoDate(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function validateFechaIncorporacion(
  value: string,
  today = getLocalIsoDate()
): string | null {
  if (!value) return "La fecha es obligatoria";

  if (!isIsoDate(value)) return "La fecha ingresada no es válida";

  if (value < EQUIPAMIENTO_MIN_FECHA_INCORPORACION) {
    return "La fecha de incorporación debe ser igual o posterior al 01/01/2010";
  }

  if (value > today) {
    return "La fecha de incorporación no puede ser posterior a la fecha actual";
  }

  return null;
}
