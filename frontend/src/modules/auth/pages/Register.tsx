import Field from "@/components/Field";
import { applyFieldErrors, focusFieldErrors } from "@/lib/httpError";
import { FormEvent, useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { CheckCircle } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { SYSTEM_SETUP_QUERY_KEY } from "@/modules/auth/hooks/useSystemSetup";
import { getErrorMessage } from "@/lib/httpError";
import RouteBreadcrumbs from "@/modules/shared/components/RouteBreadcrumbs";

export default function RegisterPage() {
  const { register, esPrimerUsuario } = useAuth();
  const nav = useNavigate();
  const queryClient = useQueryClient();

  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [esPrimero, setEsPrimero] = useState<boolean | null>(null);
  const [verificando, setVerificando] = useState(true);
  const [verificationError, setVerificationError] = useState(false);
  const [registroExitoso, setRegistroExitoso] = useState(false);

  // Verificar si es el primer usuario al cargar la página
  useEffect(() => {
    async function verificar() {
      try {
        setVerificationError(false);
        const esElPrimero = await esPrimerUsuario();
        setEsPrimero(esElPrimero);
      } catch {
        // Un fallo de verificación no debe habilitar ni ocultar el registro inicial.
        setEsPrimero(null);
        setVerificationError(true);
      } finally {
        setVerificando(false);
      }
    }
    verificar();
  }, [esPrimerUsuario]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (loading) return;
    setError(null);
    const nextErrors: Record<string, string> = {};
    if (!nombre.trim()) nextErrors.nombre = "Ingrese su nombre de usuario.";
    if (!email.trim()) nextErrors.email = "Ingrese su correo electrónico.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) nextErrors.email = "Ingrese un correo electrónico válido.";
    if (password.length < 6) nextErrors.password = "Ingrese una contraseña de al menos 6 caracteres.";
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      focusFieldErrors(nextErrors);
      return;
    }
    setLoading(true);
    try {
      await register(nombre, email, password);
      queryClient.setQueryData(SYSTEM_SETUP_QUERY_KEY, false);
      setRegistroExitoso(true);
      // Después de 2 segundos, redirigir al login
      setTimeout(() => {
        nav("/login", { replace: true });
      }, 2000);
    } catch (err: unknown) {
      if (applyFieldErrors(err, setFieldErrors, ["nombre","email","password"])) return;
      setError(getErrorMessage(err, "Lo sentimos, no pudimos crear la cuenta. Verifique los datos e intente nuevamente."));
    } finally {
      setLoading(false);
    }
  }

  // Estado de carga mientras verifica
  if (verificando) {
    return (
      <div className="min-h-screen grid place-items-center bg-[#F6F6FB]">
        <div className="card w-full max-w-md text-center">
          <RouteBreadcrumbs />
          <div className="animate-pulse">
            <div className="h-8 w-48 bg-slate-200 rounded mx-auto mb-4"></div>
            <div className="h-4 w-32 bg-slate-200 rounded mx-auto"></div>
          </div>
        </div>
      </div>
    );
  }

  if (verificationError) {
    return (
      <div className="min-h-screen grid place-items-center bg-[#F6F6FB]">
        <div className="card w-full max-w-md text-center">
          <RouteBreadcrumbs />
          <h1 className="text-xl font-semibold mb-3">No pudimos verificar la configuración</h1>
          <p className="text-slate-600 mb-6">
            Lo sentimos, no pudimos recuperar la información. Intente nuevamente antes de crear una cuenta.
          </p>
          <button type="button" onClick={() => window.location.reload()} className="inline-block w-full rounded-full bg-slate-900 text-white py-2.5 hover:opacity-90">
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // Si NO es el primer usuario, mostrar mensaje de sistema ya configurado
  if (esPrimero === false) {
    return (
      <div className="min-h-screen grid place-items-center bg-[#F6F6FB]">
        <div className="card w-full max-w-md text-center">
          <RouteBreadcrumbs />
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">🔒</span>
          </div>
          <h1 className="text-xl font-semibold mb-3">Sistema Configurado</h1>
          <p className="text-slate-600 mb-6">
            El sistema ya tiene un administrador configurado. Si necesitas acceso, contactá al administrador de tu UCT.
          </p>
          <Link
            to="/login"
            className="inline-block w-full rounded-full bg-slate-900 text-white py-2.5 hover:opacity-90"
          >
            Ir al Login
          </Link>
        </div>
      </div>
    );
  }

  // Si es el primer usuario, mostrar formulario de registro
  return (
    <div className="min-h-screen grid place-items-center bg-[#F6F6FB]">
      <div className="card w-full max-w-md">
        <RouteBreadcrumbs />
        {registroExitoso ? (
          <div className="text-center py-8">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">¡Cuenta Creada!</h2>
            <p className="text-slate-600">
              Tu cuenta de administrador ha sido creada exitosamente. Redirigiendo al login...
            </p>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <h1 className="text-2xl font-semibold">Crear Cuenta de Administrador</h1>
              <p className="text-slate-500 text-sm mt-1">
                Estás configurando el sistema por primera vez. Esta cuenta será el administrador principal.
              </p>
            </div>

            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <Field label="Nombre de usuario" required name="nombre" error={fieldErrors.nombre}>

                <input
                  className="input"
                  required
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Ingresa tu nombre de usuario"
                />
              </Field>
              <Field label="Email" required name="email" error={fieldErrors.email}>

                <input
                  className="input"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ingresa tu email"
                />
              </Field>
              <Field label="Contraseña" required name="password" error={fieldErrors.password}>

                <input
                  className="input"
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Ingresa tu contraseña"
                />
                <p className="text-xs text-slate-400 mt-1">Mínimo 6 caracteres</p>
              </Field>
              {error && <p role="alert" className="text-sm text-rose-600">{error}</p>}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-full bg-slate-900 text-white py-2.5 hover:opacity-90 disabled:opacity-60"
              >
                {loading ? "Creando cuenta…" : "Crear Cuenta de Admin"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
