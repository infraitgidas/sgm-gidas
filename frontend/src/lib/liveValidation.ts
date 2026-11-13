export type FieldErrors = Record<string, string>;

/** Revalida el campo editado y las reglas que cambiaron por su dependencia. */
export function updateLiveValidationErrors<T extends Record<string, string | undefined>>(
  previous: T,
  before: Readonly<Record<string, string | undefined>>,
  after: Readonly<Record<string, string | undefined>>,
  field: string,
): T {
  const affected = new Set([field]);
  for (const key of new Set([...Object.keys(before), ...Object.keys(after)])) {
    if (before[key] !== after[key]) affected.add(key);
  }
  const next = { ...previous };
  const fields: Record<string, string | undefined> = next;
  for (const key of affected) {
    if (after[key]) fields[key] = after[key];
    else delete fields[key];
  }
  return next;
}
