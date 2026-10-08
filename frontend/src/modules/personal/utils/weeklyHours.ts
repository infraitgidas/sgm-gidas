export const MAX_HORAS_SEMANALES = 7 * 24;
export const WEEKLY_HOURS_ERROR = "Ingrese horas semanales enteras entre 1 y 168.";

export function validWeeklyHours(hours: unknown): hours is number {
  return typeof hours === "number" && Number.isInteger(hours) && hours >= 1 && hours <= MAX_HORAS_SEMANALES;
}
