export const RESET_REQUEST_MESSAGE = "Si el correo corresponde a una cuenta habilitada, recibirá instrucciones para restablecer la contraseña. Revise también la carpeta de correo no deseado.";
export const RESET_SUCCESS_MESSAGE = "Contraseña actualizada con éxito. Inicie sesión con su nueva contraseña.";

export function isInvalidResetToken(error: unknown): boolean {
  const body = (error as { body?: { error?: { code?: string } } } | null)?.body;
  return body?.error?.code === "INVALID_PASSWORD_RESET_TOKEN";
}

export function normalizeResetEmail(value: string): string { return value.trim().toLowerCase(); }

export function validateResetEmail(value: string): Record<string, string> {
  const email = normalizeResetEmail(value);
  return email.length <= 120 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
    ? {} : { email: "Ingrese un correo electrónico válido." };
}

export function validateResetPassword(password: string, confirmation: string): Record<string, string> {
  const errors: Record<string, string> = {};
  if (password.length < 6) errors.password_nueva = "Ingrese una contraseña de al menos 6 caracteres.";
  if (new TextEncoder().encode(password).length > 72) errors.password_nueva = "La contraseña es demasiado larga. Use hasta 72 bytes.";
  if (!confirmation || password !== confirmation) errors.password_confirmacion = "La confirmación debe coincidir con la nueva contraseña.";
  return errors;
}

export function parseResetFragment(hash: string): string | null {
  if (hash.length > 500) return null;
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const tokens = params.getAll("token");
  return tokens.length === 1 && /^[A-Za-z0-9_-]{43}$/.test(tokens[0]) ? tokens[0] : null;
}

export function takeResetToken(location: Pick<Location, "hash" | "pathname" | "search"> = window.location,
  history: Pick<History, "replaceState" | "state"> = window.history): string | null {
  const token = parseResetFragment(location.hash);
  if (location.hash) history.replaceState(history.state, "", `${location.pathname}${location.search}`);
  return token;
}
