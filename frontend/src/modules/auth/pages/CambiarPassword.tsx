import Field from "@/components/Field";
import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Lock, Eye, EyeOff, CheckCircle } from "lucide-react";
import { getErrorMessage } from "@/lib/httpError";

export default function CambiarPasswordPage() {
  const { cambiarPassword, debeCambiarPassword, logout } = useAuth();
  const nav = useNavigate();

  const esPrimerLogin = debeCambiarPassword();

  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");
  const [passwordConfirmacion, setPasswordConfirmacion] = useState("");

  const [showPasswordActual, setShowPasswordActual] = useState(false);
  const [showPasswordNueva, setShowPasswordNueva] = useState(false);
  const [showPasswordConfirmacion, setShowPasswordConfirmacion] = useState(false);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exitoso, setExitoso] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (loading) return;
    setError(null);
    const nextErrors: Record<string, string> = {};
    if (!esPrimerLogin && !passwordActual.trim()) nextErrors.passwordActual = "Ingrese su contraseña actual.";
    if (passwordNueva.length < 6) nextErrors.passwordNueva = "Ingrese una contraseña de al menos 6 caracteres.";
    if (passwordNueva !== passwordConfirmacion) nextErrors.passwordConfirmacion = "La confirmación debe coincidir con la nueva contraseña.";
    if (!esPrimerLogin && passwordNueva === passwordActual) nextErrors.passwordNueva = "Ingrese una contraseña diferente de la actual.";
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      focusFieldErrors(nextErrors);
      return;
    }

    setLoading(true);

    try {
      await cambiarPassword({
        passwordNueva,
        passwordActual: esPrimerLogin ? undefined : passwordActual,
      });

      setExitoso(true);

      setTimeout(() => {
        nav("/inicio", { replace: true });
      }, 1500);
    } catch (err: unknown) {
      if (applyFieldErrors(err, setFieldErrors, ["passwordActual","passwordNueva","passwordConfirmacion"])) return;
      setError(
        getErrorMessage(err,
          "Lo sentimos, no pudimos cambiar la contraseña. Verifique los datos e intente nuevamente."
        )
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-[#F6F6FB] px-4">
      <div className="card w-full max-w-md bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
        {exitoso ? (
          <div className="text-center py-8">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">¡Contraseña Actualizada!</h2>
            <p className="text-slate-600">
              Tu contraseña ha sido cambiada exitosamente. Redirigiendo al sistema...
            </p>
          </div>
        ) : (
          <>
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <Lock className="w-8 h-8 text-amber-600" />
              </div>

              <h1 className="text-2xl font-bold text-slate-900">
                Cambiar Contraseña
              </h1>

              <p className="text-slate-500 text-sm mt-2">
                {esPrimerLogin
                  ? "Es necesario que cambies tu contraseña temporal antes de continuar."
                  : "Actualiza tu contraseña para seguir usando el sistema con seguridad."}
              </p>
            </div>

            <form onSubmit={handleSubmit} noValidate className="space-y-5">
              {!esPrimerLogin && (
                <Field label="Contraseña Actual" required name="passwordActual" error={fieldErrors.passwordActual}>


                  <div className="relative">
                    <input
                      className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 focus:border-transparent outline-none transition-all pr-10"
                      type={showPasswordActual ? "text" : "password"}
                      required
                      value={passwordActual}
                      onChange={(e) => setPasswordActual(e.target.value)}
                      placeholder="Ingresa tu contraseña actual"
                    />

                    <button
                      type="button"
                      onClick={() => setShowPasswordActual(!showPasswordActual)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    >
                      {showPasswordActual ? (
                        <EyeOff className="w-5 h-5" />
                      ) : (
                        <Eye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </Field>
              )}

              <Field label="Nueva Contraseña" required name="passwordNueva" error={fieldErrors.passwordNueva}>


                <div className="relative">
                  <input
                    className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 focus:border-transparent outline-none transition-all pr-10"
                    type={showPasswordNueva ? "text" : "password"}
                    required
                    minLength={6}
                    value={passwordNueva}
                    onChange={(e) => setPasswordNueva(e.target.value)}
                    placeholder="Mínimo 6 caracteres"
                  />

                  <button
                    type="button"
                    onClick={() => setShowPasswordNueva(!showPasswordNueva)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPasswordNueva ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>

                <p className="text-xs text-slate-400 mt-1">
                  Mínimo 6 caracteres
                </p>
              </Field>

              <Field label="Confirmar Nueva Contraseña" required name="passwordConfirmacion" error={fieldErrors.passwordConfirmacion}>


                <div className="relative">
                  <input
                    className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 focus:border-transparent outline-none transition-all pr-10"
                    type={showPasswordConfirmacion ? "text" : "password"}
                    required
                    value={passwordConfirmacion}
                    onChange={(e) => setPasswordConfirmacion(e.target.value)}
                    placeholder="Repite la nueva contraseña"
                  />

                  <button
                    type="button"
                    onClick={() =>
                      setShowPasswordConfirmacion(!showPasswordConfirmacion)
                    }
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPasswordConfirmacion ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </Field>

              {error && (
                <div
                  role="alert"
                  className="bg-rose-50 text-rose-600 text-sm px-4 py-3 rounded-lg border border-rose-100 flex items-center gap-2"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" x2="12" y1="8" y2="12" />
                    <line x1="12" x2="12.01" y1="16" y2="16" />
                  </svg>
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-full bg-slate-900 text-white font-medium py-3 hover:bg-slate-800 disabled:opacity-70 disabled:cursor-not-allowed transition-all shadow-lg shadow-slate-900/20"
              >
                {loading ? "Cambiando..." : "Cambiar Contraseña"}
              </button>

              {esPrimerLogin && (
                <button
                  type="button"
                  onClick={logout}
                  className="w-full text-slate-500 text-sm py-2 hover:text-slate-700 transition-colors"
                >
                  Cancelar y salir
                </button>
              )}
            </form>
          </>
        )}
      </div>
    </div>
  );
}
