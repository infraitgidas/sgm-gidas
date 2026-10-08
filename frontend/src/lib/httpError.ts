export type ApiErrorBody = {
  error?:
    | string
    | {
        code?: unknown;
        message?: unknown;
        details?: unknown;
      }
    | null;
  message?: unknown;
  detail?: unknown;
  fields?: unknown;
  requestId?: unknown;
};

function nonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function getApiErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object" || Array.isArray(body)) return null;

  const parsed = body as ApiErrorBody;
  if (parsed.error && typeof parsed.error === "object") {
    const nestedMessage = nonEmptyString(parsed.error.message);
    if (nestedMessage) return nestedMessage;
  }

  return (
    nonEmptyString(parsed.error) ??
    nonEmptyString(parsed.message) ??
    nonEmptyString(parsed.detail)
  );
}

export function getErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (!error || typeof error !== "object") return fallback;

  const candidate = error as { body?: unknown; message?: unknown };
  const message = (
    getApiErrorMessage(candidate.body) ??
    nonEmptyString(candidate.message) ??
    fallback
  );
  return isSafeMessage(message) ? message : fallback;
}

function isSafeMessage(message: string): boolean {
  return !/^(?:Bad Request|Unauthorized|Forbidden|Not Found|Conflict|Internal Server Error|Failed to fetch|NetworkError)$/i.test(message) &&
    !/traceback|sqlalchemy|psycopg|sqlite|postgres(?:ql)?|SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+.+\s+SET|DELETE\s+FROM|\b(?:table|column|constraint)\b|password\s*=|https?:\/\/|[A-Za-z]:[\\/]|\b[a-zA-Z]+(?:_[a-zA-Z0-9]+)+\b|referencia de seguimiento|request.?id/i.test(message);
}

function errorContract(error: unknown): Record<string, unknown> | null {
  if (!error || typeof error !== "object") return null;
  const body = (error as { body?: unknown }).body;
  if (!body || typeof body !== "object" || Array.isArray(body)) return null;
  const nested = (body as { error?: unknown }).error;
  return nested && typeof nested === "object" && !Array.isArray(nested)
    ? nested as Record<string, unknown> : body as Record<string, unknown>;
}

export function getApiFieldErrors(error: unknown): Record<string, string> {
  const contract = errorContract(error);
  const details = contract?.details as Record<string, unknown> | undefined;
  const fields = details?.fields ?? contract?.fields;
  if (!fields || typeof fields !== "object" || Array.isArray(fields)) return {};
  return Object.fromEntries(Object.entries(fields).flatMap(([key, value]) => {
    const message = nonEmptyString(value);
    return message && isSafeMessage(message) ? [[key, message]] : [];
  }));
}

const fieldAliases: Record<string, string[]> = {
  nombre_apellido: ["nombre", "nombreApellido"], horas_semanales: ["horas", "horasSemanales"],
  tipo_personal_id: ["tipoPersonal", "tipoPersonalId"], tipo_formacion_id: ["tipoFormacion", "tipoFormacionId"],
  tipo_dedicacion_id: ["dedicacion", "dedicacionId"], categoria_utn_id: ["categoria", "categoriaId"],
  programa_incentivos_id: ["programa", "programaId"], grupo_utn_id: ["grupo", "grupoUtnId"],
  nombre_usuario: ["nombre", "usuario", "nombreUsuario"], mail: ["email", "correo"], rol_id: ["rol"],
  id_investigador: ["investigador", "investigadorId", "investigadores", "investigadoresIds"],
  investigador_id: ["investigador", "investigadorId", "investigadores", "investigadoresIds"],
  investigadores: ["investigadoresIds"], becarios: ["becariosIds"],
  id_becario: ["becarios", "becariosIds"], proyecto_id: ["proyecto"], es_coordinador: ["coordinadorId"],
  fecha_fin: ["fechaFin", "fechaFinalizacion"], fecha_publicacion: ["fecha", "fechaPublicacion"],
  descripcion_breve: ["descripcion"], monto_invertido: ["monto"],
  tipo_erogacion_id: ["tipo", "tipoId"], fuente_financiamiento_id: ["fuente", "fuenteId", "fuenteFinanciamientoId"],
  numero_erogacion: ["numero"], monto_erogacion: ["monto"], fecha_erogacion: ["fecha"],
  tipo_contrato_id: ["tipoContrato", "tipoContratoId"], numero_transferencia: ["numero", "numeroTransferencia"],
  grado_academico_id: ["gradoAcademico", "gradoAcademicoId"], rol_actividad_id: ["rolActividad", "rolActividadId"],
  tipo_id: ["tipoId", "tipo"], tipo_registro_id: ["tipoRegistro", "tipoId"],
  nombre_articulo: ["nombreArticulo", "nombre"], organismo_registrante: ["organismo", "organismoRegistrante"],
  facultad_regional: ["facultadRegional"], nombre_sigla_grupo: ["nombreSigla"], correo_electronico: ["correo"],
  tipo_visita_id: ["tipoVisita"], nombre_evento: ["nombreEvento"],
  forma_participacion: ["formaParticipacion"],
  nombre_unidad_academica: ["facultadRegional"], objetivo_desarrollo: ["objetivos"],
  proyecto_investigacion_id: ["proyecto"],
  titulo_trabajo: ["titulo"], nombre_reunion: ["nombreReunion"],
  tipo_reunion_id: ["tipoId"], tipo_revista_id: ["tipoId"],
  fecha_presentacion: ["fechaPresentacion"],
  periodo_inicio: ["periodoInicio"], periodo_fin: ["periodoFin"],
  fecha_apertura: ["fechaApertura"],
  adoptantes_ids: ["adoptantes"],
  becas: ["becaGlobal"],
};

export function mapFieldErrors(error: unknown, controls: readonly string[]): Record<string, string> {
  const mapped: Record<string, string> = {};
  for (const [key, message] of Object.entries(getApiFieldErrors(error))) {
    const camel = key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
    const target = [key, camel, ...(fieldAliases[key] ?? [])].find(name => controls.includes(name));
    if (target) mapped[target] = message;
  }
  return mapped;
}

export function focusFieldErrors(fields: Record<string, string>, root: ParentNode = document): void {
  requestAnimationFrame(() => {
    const wrappers = root.querySelectorAll<HTMLElement>("[data-error-field]");
    for (const wrapper of wrappers) {
      if (!Object.prototype.hasOwnProperty.call(fields, wrapper.dataset.errorField ?? "")) continue;
      const control = wrapper.querySelector<HTMLElement>("input:not(:disabled):not([type=hidden]), select:not(:disabled), textarea:not(:disabled), button:not(:disabled), [tabindex]:not([disabled])");
      (control ?? wrapper).focus();
      break;
    }
  });
}

export function applyFieldErrors<T extends Record<string, string | undefined>>(
  error: unknown,
  setErrors: (update: (previous: T) => T) => void,
  controls: readonly string[],
): boolean {
  const fields = mapFieldErrors(error, controls);
  if (!Object.keys(fields).length) return false;
  setErrors(previous => ({ ...previous, ...fields }));
  focusFieldErrors(fields);
  // Unknown controls still need a general message; never silently discard them.
  return Object.keys(fields).length === Object.keys(getApiFieldErrors(error)).length;
}
