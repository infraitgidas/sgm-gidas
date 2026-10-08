export const MAX_ENLACE = 2048;
export function errorEnlace(valor: string): string | undefined {
  const enlace = valor.trim();
  if (!enlace) return undefined;
  const mensaje = "Ingrese un enlace HTTP o HTTPS válido, de hasta 2048 caracteres.";
  if (/^https?:\/\/[^/?#]*@/i.test(enlace)) return mensaje;
  if (enlace.length > MAX_ENLACE || /[\s\x00-\x1f\x7f\\]/.test(enlace) || !/^https?:\/\//i.test(enlace)) return mensaje;
  try {
    const url = new URL(enlace);
    if (!url.hostname.startsWith("[") && !/^[A-Za-z0-9.-]+$/.test(url.hostname)) return mensaje;
    if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password) return mensaje;
  } catch { return mensaje; }
  return undefined;
}
export function enlaceSeguro(valor?: string | null): string | null {
  return valor?.trim() && !errorEnlace(valor) ? valor.trim() : null;
}
