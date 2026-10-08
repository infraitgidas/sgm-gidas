export function calendarValidationMessage(
  input: string,
  parsed: Date | null,
  minDate?: Date,
  maxDate?: Date
): string {
  if (!input.trim()) return "";
  if (!parsed) return "Ingrese una fecha válida con formato DD/MM/AAAA.";
  const day = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const format = (date: Date) => `${String(date.getDate()).padStart(2, "0")}/${String(date.getMonth() + 1).padStart(2, "0")}/${date.getFullYear()}`;
  if (minDate && day(parsed) < day(minDate)) {
    return `Fechas válidas desde ${format(minDate)}.`;
  }
  if (maxDate && day(parsed) > day(maxDate)) {
    return `No se pueden fechas posteriores al ${format(maxDate)}.`;
  }
  return "";
}
