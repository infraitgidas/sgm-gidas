export function hasLetter(value: string): boolean {
  return /\p{L}/u.test(value);
}

export function hasOnlyLettersAndSpaces(value: string): boolean {
  return /^\p{L}+(?: +\p{L}+)*$/u.test(value.trim());
}
