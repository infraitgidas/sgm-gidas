import { useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Mail, CheckCircle } from "lucide-react";
import Button from "@/components/Button";
import Field from "@/components/Field";
import { applyFieldErrors, focusFieldErrors, getErrorMessage } from "@/lib/httpError";
import { useRequestPasswordReset } from "@/modules/auth/hooks/usePasswordReset";
import { normalizeResetEmail, RESET_REQUEST_MESSAGE, validateResetEmail } from "@/modules/auth/utils/passwordReset";

export default function RecuperarPassword() {
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const request = useRequestPasswordReset();
  const sending = useRef(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (sending.current) return;
    const nextErrors = validateResetEmail(email);
    setErrors(nextErrors); setError("");
    if (Object.keys(nextErrors).length) return focusFieldErrors(nextErrors);
    sending.current = true;
    try { await request.mutateAsync(normalizeResetEmail(email)); setSent(true); setEmail(""); }
    catch (err) { if (!applyFieldErrors(err, setErrors, ["email"])) setError(getErrorMessage(err, "Lo sentimos, no pudimos procesar la solicitud. Intente nuevamente.")); }
    finally { sending.current = false; }
  }

  return <div className="min-h-screen grid place-items-center bg-[#F6F6FB] px-4 py-8">
    <main className="card w-full max-w-md rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
      <div className="mb-6 text-center">
        <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-full bg-amber-50"><Mail aria-hidden="true" className="h-8 w-8 text-amber-600" /></div>
        <h1 className="text-2xl font-semibold text-slate-900">Recuperar contraseña</h1>
        <p className="mt-2 text-sm text-slate-600">Ingrese el correo asociado a su cuenta para recibir un enlace de restablecimiento.</p>
      </div>
      {sent ? <div role="status" aria-live="polite" className="space-y-3 text-sm text-slate-700">
        <CheckCircle aria-hidden="true" className="mx-auto h-10 w-10 text-emerald-600" /><p>{RESET_REQUEST_MESSAGE}</p>
        <p>Si no puede acceder a ese correo, comuníquese con el administrador para verificar su identidad y actualizarlo.</p>
      </div> : <form onSubmit={submit} noValidate className="space-y-5">
        <Field label="Correo electrónico" name="email" required error={errors.email}>
          <input id="email" type="email" autoComplete="email" maxLength={120} className="input w-full" value={email}
            disabled={request.isPending} placeholder="Ej: usuario@institucion.edu.ar"
            onChange={event => { setEmail(event.target.value); if (errors.email) setErrors(validateResetEmail(event.target.value)); }}
            onBlur={() => setErrors(validateResetEmail(email))} />
        </Field>
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        <Button type="submit" className="w-full" loading={request.isPending} loadingText="Enviando solicitud...">Enviar enlace</Button>
      </form>}
      <Link to="/login" className="mt-6 block text-center text-sm font-medium text-slate-600 hover:text-slate-950">Volver a iniciar sesión</Link>
    </main>
  </div>;
}
