import { useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Lock, Eye, EyeOff } from "lucide-react";
import Button from "@/components/Button";
import Field from "@/components/Field";
import { applyFieldErrors, focusFieldErrors, getErrorMessage } from "@/lib/httpError";
import { useConfirmPasswordReset } from "@/modules/auth/hooks/usePasswordReset";
import { isInvalidResetToken, RESET_SUCCESS_MESSAGE, takeResetToken, validateResetPassword } from "@/modules/auth/utils/passwordReset";

export default function RestablecerPassword() {
  const [token, setToken] = useState(takeResetToken);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const confirm = useConfirmPasswordReset();
  const sending = useRef(false);
  const navigate = useNavigate();

  function validate(field: string, nextPassword = password, nextConfirmation = confirmation) {
    const next = validateResetPassword(nextPassword, nextConfirmation);
    setErrors(previous => ({ ...previous, [field]: next[field] ?? "",
      ...(field === "password_nueva" && previous.password_confirmacion ? { password_confirmacion: next.password_confirmacion ?? "" } : {}) }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (sending.current || !token) return;
    const nextErrors = validateResetPassword(password, confirmation);
    setErrors(nextErrors); setError("");
    if (Object.keys(nextErrors).length) return focusFieldErrors(nextErrors);
    sending.current = true;
    try {
      await confirm.mutateAsync({ token, password_nueva: password, password_confirmacion: confirmation });
      setToken(null); setPassword(""); setConfirmation("");
      navigate("/login", { replace: true, state: { successMessage: RESET_SUCCESS_MESSAGE } });
    } catch (err) {
      if (isInvalidResetToken(err)) { setToken(null); setPassword(""); setConfirmation(""); }
      if (!applyFieldErrors(err, setErrors, ["password_nueva", "password_confirmacion"])) setError(getErrorMessage(err, "Lo sentimos, no pudimos restablecer la contraseña. Intente nuevamente."));
    } finally { sending.current = false; }
  }

  return <div className="min-h-screen grid place-items-center bg-[#F6F6FB] px-4 py-8">
    <main className="card w-full max-w-md rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
      <div className="mb-6 text-center">
        <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-full bg-amber-50"><Lock aria-hidden="true" className="h-8 w-8 text-amber-600" /></div>
        <h1 className="text-2xl font-semibold text-slate-900">Modificar contraseña</h1>
        <p className="mt-2 text-sm text-slate-600">Elija una nueva contraseña para su cuenta.</p>
      </div>
      {!token ? <div role="alert" className="space-y-4 text-sm text-slate-700">
        <p>{error || "El enlace no es válido o ya no está disponible. Solicite uno nuevo para continuar."}</p>
        <Link to="/recuperar-password" className="font-semibold text-slate-950 underline">Solicitar un nuevo enlace</Link>
      </div> : <form onSubmit={submit} noValidate className="space-y-5">
        <Field label="Nueva Contraseña" name="password_nueva" required error={errors.password_nueva}>
          <input id="password_nueva" type={visible ? "text" : "password"} autoComplete="new-password" className="input w-full" value={password}
            disabled={confirm.isPending} placeholder="Al menos 6 caracteres" aria-describedby="password-reset-help"
            onChange={event => { setPassword(event.target.value); if (errors.password_nueva || errors.password_confirmacion) validate("password_nueva", event.target.value); }} onBlur={() => validate("password_nueva")} />
        </Field>
        <p id="password-reset-help" className="text-xs text-slate-500">Use una contraseña de al menos 6 caracteres.</p>
        <Field label="Repetir Contraseña" name="password_confirmacion" required error={errors.password_confirmacion}>
          <input id="password_confirmacion" type={visible ? "text" : "password"} autoComplete="new-password" className="input w-full" value={confirmation}
            disabled={confirm.isPending} placeholder="Repita la nueva contraseña"
            onChange={event => { setConfirmation(event.target.value); if (errors.password_confirmacion) validate("password_confirmacion", password, event.target.value); }} onBlur={() => validate("password_confirmacion")} />
        </Field>
        <button type="button" disabled={confirm.isPending} aria-pressed={visible} onClick={() => setVisible(value => !value)} className="inline-flex items-center gap-2 text-sm text-slate-600">
          {visible ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}{visible ? "Ocultar contraseñas" : "Mostrar contraseñas"}
        </button>
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        <Button type="submit" className="w-full" loading={confirm.isPending} loadingText="Guardando...">Guardar contraseña</Button>
      </form>}
      <Link to="/login" className="mt-6 block text-center text-sm font-medium text-slate-600 hover:text-slate-950">Volver a iniciar sesión</Link>
    </main>
  </div>;
}
