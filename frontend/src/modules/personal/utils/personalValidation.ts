// @ts-ignore Node ejecuta las pruebas de dominio sin un bundler.
import { hasOnlyLettersAndSpaces } from "../../../lib/textValidation.ts";

export function validatePersonalName(nombre: string, apellido: string): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [campo, valor] of [["nombre", nombre], ["apellido", apellido]]) {
    const max = 60;
    if (!valor.trim()) errors[campo] = "Complete este campo.";
    else if (!hasOnlyLettersAndSpaces(valor) || valor.trim().length > max)
      errors[campo] = `Use solo letras y espacios, hasta ${max} caracteres.`;
  }
  if (nombre.trim().length + apellido.trim().length + 1 > 120 && apellido.trim())
    errors.apellido = "Nombre y apellido deben sumar hasta 120 caracteres.";
  return errors;
}

export function validatePersonalStartDate(value: Date | null, today = new Date()): string | null {
  if (!value || !Number.isFinite(value.getTime())) return "Ingrese una fecha de alta válida.";
  const end = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const start = new Date(value.getFullYear(), value.getMonth(), value.getDate());
  if (start < new Date(2010, 0, 1) || start > end)
    return "Ingrese una fecha de alta válida entre el 01/01/2010 y hoy.";
  return null;
}

/** Actualiza los campos validados y conserva los errores ajenos a la interacción. */
export function updatePersonalErrors(
  previous: Record<string, string>,
  fields: Record<string, string | null | undefined>,
): Record<string, string> {
  const next = { ...previous };
  for (const [field, message] of Object.entries(fields)) {
    if (message) next[field] = message;
    else delete next[field];
  }
  return next;
}
