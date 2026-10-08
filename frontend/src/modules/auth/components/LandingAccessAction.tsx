import { ArrowRight, LoaderCircle, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import type { AccessState } from "@/modules/auth/utils/landingAccessState";

type LandingAccessActionProps = {
  state: AccessState;
  retrying: boolean;
  supportEmail: string;
  onRetry: () => Promise<void>;
};

export default function LandingAccessAction({
  state,
  retrying,
  supportEmail,
  onRetry,
}: LandingAccessActionProps) {
  if (state === "loading") {
    return (
      <div
        className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-slate-100 px-4 text-sm font-medium text-slate-600"
        role="status"
        aria-live="polite"
      >
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
        Verificando acceso…
      </div>
    );
  }

  if (state === "error") {
    return (
      <div
        className="max-w-2xl rounded-xl border border-amber-200 bg-amber-50/70 p-4 sm:p-5"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-start gap-3">
          <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-amber-200 bg-white text-amber-700">
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-amber-800">
              Estado de acceso
            </p>
            <h2 className="mt-1 text-base font-semibold text-slate-950 sm:text-lg">
              No pudimos verificar la configuración del sistema
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              La verificación no está disponible en este momento. No es posible
              determinar si debe iniciar sesión o crear el administrador inicial.
            </p>
            <div className="mt-4 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
              <button
                type="button"
                onClick={() => void onRetry()}
                disabled={retrying}
                className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 focus-visible:ring-offset-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {retrying ? (
                  <LoaderCircle
                    className="h-4 w-4 animate-spin"
                    aria-hidden="true"
                  />
                ) : (
                  <RefreshCw className="h-4 w-4" aria-hidden="true" />
                )}
                {retrying ? "Verificando…" : "Reintentar verificación"}
              </button>
              <p className="text-xs leading-5 text-slate-500">
                Si el problema continúa, contacte a{" "}
                <a
                  href={`mailto:${supportEmail}`}
                  className="font-semibold text-slate-700 underline decoration-slate-300 underline-offset-2 transition hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2"
                >
                  {supportEmail}
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const destination =
    state === "first-admin"
      ? "/registro"
      : state === "authenticated"
        ? "/inicio"
        : "/login";
  const label =
    state === "first-admin"
      ? "Configurar administrador inicial"
      : state === "authenticated"
        ? "Abrir panel de gestión"
        : "Iniciar sesión";

  return (
    <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:gap-4">
      <Link
        to={destination}
        className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2"
      >
        {label}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
      <p className="text-xs text-slate-500">
        Personal autorizado · acceso con credenciales institucionales
      </p>
    </div>
  );
}
