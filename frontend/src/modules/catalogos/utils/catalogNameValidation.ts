export function hasDescriptiveCatalogName(value: string): boolean {
  return /\p{L}/u.test(value.trim());
}
