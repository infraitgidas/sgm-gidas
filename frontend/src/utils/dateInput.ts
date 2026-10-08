export function formatDateInput(value: string): string {
  // Keep separators already present so editing a selected day, month or year
  // does not shift the other parts of an existing date.
  if (value.includes("/")) {
    const clean = value.replace(/[^\d/]/g, "");
    const unfinishedMonth = clean.match(/^(\d{2})\/(\d{3,})$/);
    if (unfinishedMonth) {
      return `${unfinishedMonth[1]}/${unfinishedMonth[2].slice(0, 2)}/${unfinishedMonth[2].slice(2, 6)}`;
    }
    return clean.slice(0, 10);
  }

  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

export function replaceDateDigit(value: string, cursor: number, digit: string) {
  if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value) || !/^\d$/.test(digit)) return null;
  const position = value[cursor] === "/" ? cursor + 1 : cursor;
  if (position < 0 || position >= value.length) return null;
  const nextCursor = position + 1 + (value[position + 1] === "/" ? 1 : 0);
  return {
    value: `${value.slice(0, position)}${digit}${value.slice(position + 1)}`,
    cursor: nextCursor,
  };
}
