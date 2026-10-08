const fieldNames: Record<string, string> = {
  nombre_apellido: "nombre",
  dni: "dni",
  cuil: "cuil",
  horas_semanales: "horas",
  tipo_personal_id: "tipoPersonal",
  fecha_alta_grupo: "fechaAltaGrupo",
  grupo_utn_id: "grupo",
};

export function personalFieldErrors(error: unknown): Record<string, string> {
  if (!error || typeof error !== "object") return {};
  const body = (error as { body?: unknown }).body;
  if (!body || typeof body !== "object") return {};
  const apiError = (body as { error?: unknown }).error;
  if (!apiError || typeof apiError !== "object") return {};
  const details = (apiError as { details?: unknown }).details;
  if (!details || typeof details !== "object") return {};
  const fields = (details as { fields?: unknown }).fields;
  if (!fields || typeof fields !== "object" || Array.isArray(fields)) return {};
  return Object.fromEntries(Object.entries(fields).flatMap(([key, value]) =>
    fieldNames[key] && typeof value === "string" && value.trim()
      ? [[fieldNames[key], value]] : []
  ));
}
