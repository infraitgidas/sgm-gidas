const CIVIL_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const ISO_TIMESTAMP_WITHOUT_ZONE =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;

export const INSTITUTIONAL_MIN_DATE_ISO = "2010-01-01";

function isValidDate(value: Date) {
  return !Number.isNaN(value.getTime());
}

export function parseCivilDate(value?: string | Date | null): Date | null {
  if (value instanceof Date) {
    if (!isValidDate(value)) return null;
    return new Date(value.getFullYear(), value.getMonth(), value.getDate());
  }

  if (typeof value !== "string") return null;

  const match = CIVIL_DATE_PATTERN.exec(value);
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(year, month - 1, day);

  return parsed.getFullYear() === year &&
    parsed.getMonth() === month - 1 &&
    parsed.getDate() === day
    ? parsed
    : null;
}

export function toCivilDateString(value?: Date | null): string | null {
  if (!value || !isValidDate(value)) return null;

  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function getInstitutionalMinDate(): Date {
  return new Date(2010, 0, 1);
}

export function getLocalTodayIso(): string {
  return toCivilDateString(new Date()) ?? "";
}

export function isInstitutionalDate(value?: string | Date | null): boolean {
  const parsed = parseCivilDate(value);
  return parsed !== null && parsed >= getInstitutionalMinDate();
}

export function getCivilYear(value?: string | Date | null): number | null {
  return parseCivilDate(value)?.getFullYear() ?? null;
}

export function formatFecha(
  value?: string | Date | null,
  fallback = "—"
): string {
  const date = parseCivilDate(value);
  if (!date) return fallback;

  return new Intl.DateTimeFormat("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

export function parseApiTimestamp(value?: string | null): Date | null {
  if (!value) return null;

  const normalized = ISO_TIMESTAMP_WITHOUT_ZONE.test(value) ? `${value}Z` : value;
  const parsed = new Date(normalized);
  return isValidDate(parsed) ? parsed : null;
}

export function formatFechaHora(
  value?: string | null,
  fallback = "-"
): string {
  const date = parseApiTimestamp(value);
  return date ? date.toLocaleString("es-AR") : fallback;
}
