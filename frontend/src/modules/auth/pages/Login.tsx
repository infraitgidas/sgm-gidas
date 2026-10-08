import Field from "@/components/Field";
import { applyFieldErrors, getErrorMessage } from "@/lib/httpError";
import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, Eye, EyeOff, LoaderCircle, LogIn } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useSystemSetup } from "@/modules/auth/hooks/useSystemSetup";
import RouteBreadcrumbs from "@/modules/shared/components/RouteBreadcrumbs";
import {
  consumeSessionEnded,
  consumeSessionPath,
  isSafeInternalPath,
} from "@/modules/auth/utils/sessionNavigation";

export default function LoginPage() {
  const { login, user, loading: sessionLoading } = useAuth();
  const { data: needsInitialAdmin, isFetching: setupFetching } = useSystemSetup();
  const nav = useNavigate();
  const location = useLocation() as {
    state?: { from?: { pathname?: string; search?: string; hash?: string } };
  };
  const [from] = useState(() => {
    const statePath = location.state?.from
      ? `${location.state.from.pathname ?? ""}${location.state.from.search ?? ""}${location.state.from.hash ?? ""}`
      : "";
    if (statePath && isSafeInternalPath(statePath)) return statePath;
    return consumeSessionPath() ?? "/inicio";
  });

  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionLoading && user) {
      nav(user.primer_login ? "/cambiar-password" : from, { replace: true });
    } else if (!sessionLoading) {
      setSessionEnded(consumeSessionEnded());
    }
  }, [from, nav, sessionLoading, user]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!usuario.trim() || !password.trim()) {
      setError("Complete usuario y contraseña para ingresar al sistema.");
      return;
    }

    setLoading(true);
    try {
      const auth = await login(usuario, password);
      nav(auth.user.primer_login ? "/cambiar-password" : from, { replace: true });
    } catch (err: unknown) {
      if (applyFieldErrors(err, setFieldErrors, ["usuario","password"])) return;
      setError(
        getErrorMessage(err, "Lo sentimos, no pudimos iniciar sesión. Verifique los datos e intente nuevamente.")
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F6F6FB] px-4 py-8 sm:py-12">
      <div className="mx-auto w-full max-w-md">
        <RouteBreadcrumbs />

        <div className="card w-full border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-5 grid h-12 w-12 place-items-center rounded-lg bg-slate-950 text-white">
              <LogIn className="h-6 w-6" aria-hidden="true" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Iniciar sesión</h1>
            <p className="mt-1 text-sm text-slate-500">
              Ingrese sus credenciales para acceder al sistema.
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            {sessionEnded && (
              <p role="alert" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                Su sesión terminó. Inicie sesión nuevamente para continuar.
              </p>
            )}
            <Field label="Nombre de usuario" required name="usuario" error={fieldErrors.usuario}>

              <input
                id="usuario"
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none transition focus:border-transparent focus:ring-2 focus:ring-slate-900"
                type="text"
                required
                value={usuario}
                onChange={(event) => setUsuario(event.target.value)}
                placeholder="Ej: juanperez"
                autoComplete="username"
              />
            </Field>

            <Field label="Contraseña" required name="password" error={fieldErrors.password}>

              <div className="relative">
                <input
                  id="password"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2.5 pr-11 outline-none transition focus:border-transparent focus:ring-2 focus:ring-slate-900"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  className="absolute right-2 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                  title={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  aria-pressed={showPassword}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" aria-hidden="true" />
                  ) : (
                    <Eye className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>
              </div>
            </Field>

            {error && (
              <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || sessionLoading}
              className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <LoaderCircle className="h-5 w-5 animate-spin" aria-hidden="true" />
                  Ingresando...
                </>
              ) : (
                "Ingresar"
              )}
            </button>
          </form>

          {needsInitialAdmin === true && !setupFetching && (
            <p className="mt-7 text-center text-sm text-slate-600">
              El sistema aún no está configurado.{" "}
              <Link to="/registro" className="font-semibold text-slate-950 hover:underline">
                Crear administrador inicial
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
