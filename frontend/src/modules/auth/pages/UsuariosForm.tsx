import { applyFieldErrors, focusFieldErrors, getApiFieldErrors, mapFieldErrors } from "@/lib/httpError";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { crearUsuario, rolToRolId } from "@/modules/auth/services/usuariosService";
import { getErrorMessage } from "@/lib/httpError";
import { generateTemporaryPassword } from "@/modules/auth/utils/password";
import type { Rol } from "@/modules/auth/services/authService";
import Button from "@/components/Button";
import Field from "@/components/Field";
import {
  UserPlus,
  Eye,
  EyeOff,
  CheckCircle,
  Copy,
  Loader2,
  BookOpen,
} from "lucide-react";

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidUsername(username: string): boolean {
  return /^[a-zA-Z0-9._-]+$/.test(username);
}

export default function UsuariosForm() {
  const nav = useNavigate();
  const queryClient = useQueryClient();

  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rol, setRol] = useState<Rol>("GESTOR");
  const [showPassword, setShowPassword] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);

  const [creado, setCreado] = useState(false);
  const [usuarioCreado, setUsuarioCreado] = useState<{
    nombre: string;
    password: string;
    rol: Rol;
  } | null>(null);

  const [errors, setErrors] = useState<{
    nombre?: string;
    email?: string;
    password?: string;
    rol?: string;
  }>({});

  const crearMutation = useMutation({
    mutationFn: crearUsuario,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["usuarios"] });
      setCreado(true);
      setUsuarioCreado({ nombre, password, rol });
    },
    onError: (error) => {
      applyFieldErrors(error, setErrors, ["nombre","email","password","rol"]);
    },
  });

  function validateForm(): boolean {
    const newErrors: typeof errors = {};

    if (!nombre.trim()) {
      newErrors.nombre = "El nombre de usuario es obligatorio";
    } else if (nombre.length < 3) {
      newErrors.nombre = "El nombre debe tener al menos 3 caracteres";
    } else if (!isValidUsername(nombre)) {
      newErrors.nombre =
        "Solo letras, números, puntos, guiones y guiones bajos";
    }

    if (!email.trim()) {
      newErrors.email = "El email es obligatorio";
    } else if (!isValidEmail(email)) {
      newErrors.email = "Ingresa un email válido";
    }

    if (!password) {
      newErrors.password = "La contraseña es obligatoria";
    } else if (password.length < 6) {
      newErrors.password = "La contraseña debe tener al menos 6 caracteres";
    }

    if (rol !== "GESTOR" && rol !== "LECTURA") {
      newErrors.rol = "Debes seleccionar un rol válido";
    }

    setErrors(newErrors);
    if (Object.keys(newErrors).length) focusFieldErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (crearMutation.isPending) return;

    if (!validateForm()) return;

    crearMutation.mutate({
      nombre_usuario: nombre,
      mail: email,
      password,
      rol_id: rolToRolId(rol),
    });
  }

  function handleNombreChange(value: string) {
    setNombre(value);
    if (errors.nombre) {
      setErrors((prev) => ({ ...prev, nombre: undefined }));
    }
  }

  function handleEmailChange(value: string) {
    setEmail(value);
    if (errors.email) {
      setErrors((prev) => ({ ...prev, email: undefined }));
    }
  }

  function handlePasswordChange(value: string) {
    setPassword(value);
    if (errors.password) {
      setErrors((prev) => ({ ...prev, password: undefined }));
    }
  }

  function handleRolChange(value: Rol) {
    setRol(value);
    if (errors.rol) {
      setErrors((prev) => ({ ...prev, rol: undefined }));
    }
  }

  async function copiarPassword() {
    if (usuarioCreado) {
      try {
        await navigator.clipboard.writeText(usuarioCreado.password);
        setCopyError(null);
        setCopiado(true);
        setTimeout(() => setCopiado(false), 2000);
      } catch {
        setCopyError("No pudimos copiar la contraseña. Selecciónela manualmente e intente nuevamente.");
      }
    }
  }

  function generarPassword() {
    try {
      setPassword(generateTemporaryPassword());
      setCopyError(null);
    } catch (error) {
      if (applyFieldErrors(error, setErrors, ["nombre","email","password","rol"])) return;
      setErrors((prev) => ({
        ...prev,
        password: getErrorMessage(error, "No pudimos generar una contraseña segura. Intente nuevamente."),
      }));
      return;
    }
    if (errors.password) {
      setErrors((prev) => ({ ...prev, password: undefined }));
    }
  }

  function getRolLabel(rol: Rol) {
    if (rol === "GESTOR") return "Gestor";
    if (rol === "LECTURA") return "Lector";
    return rol;
  }

  if (creado && usuarioCreado) {
    return (
      <section className="w-full max-w-2xl mx-auto">
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-slate-900" />
          </div>

          <h2 className="text-2xl font-semibold mb-2">
            ¡Usuario Creado Exitosamente!
          </h2>

          <p className="text-slate-600 mb-6">
            El usuario <strong>{usuarioCreado.nombre}</strong> ha sido creado con
            éxito con rol <strong>{getRolLabel(usuarioCreado.rol)}</strong>.
          </p>

          <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-6 mb-6">
            <p className="text-sm text-slate-600 mb-2">Contraseña temporal:</p>
            <div className="flex items-center gap-2 justify-center">
              <code className="bg-white border border-slate-200 px-3 py-1.5 rounded-lg font-mono text-lg">
                {usuarioCreado.password}
              </code>
              <button
                onClick={() => void copiarPassword()}
                type="button"
                className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-200 rounded-lg transition-colors"
                title="Copiar contraseña"
              >
                {copiado ? "¡Copiado!" : <Copy className="w-4 h-4" />}
              </button>
            </div>
            {copyError && <p className="mt-2 text-sm text-rose-600">{copyError}</p>}
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 mb-6 text-left">
            <p className="text-sm text-slate-600">
              <strong>Importante:</strong> Compartí esta contraseña de forma segura
              con el usuario. Deberá cambiarla en su primer inicio de sesión.
            </p>
          </div>

          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => nav("/administracion")}
              className="flex-1"
            >
              Volver a Administración
            </Button>

            <Button
              variant="primary"
              onClick={() => {
                setCreado(false);
                setUsuarioCreado(null);
                setNombre("");
                setEmail("");
                setPassword("");
                setRol("GESTOR");
                setErrors({});
              }}
              className="flex-1"
            >
              Crear Otro Usuario
            </Button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="w-full">
      <h2 className="text-2xl md:text-3xl font-semibold leading-none">
        Nuevo Usuario
      </h2>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6">
        <form onSubmit={handleSubmit} noValidate className="space-y-6">
          <Field label="Nombre de Usuario" required error={errors.nombre} name="nombre">
            <input
              type="text"
              className={`input ${errors.nombre ? "border-rose-300" : ""}`}
              value={nombre}
              onChange={(e) => handleNombreChange(e.target.value)}
              placeholder="Ej: juan.perez"
              disabled={crearMutation.isPending}
            />
          </Field>

          <Field label="Email" required error={errors.email} name="email">
            <input
              type="email"
              className={`input ${errors.email ? "border-rose-300" : ""}`}
              value={email}
              onChange={(e) => handleEmailChange(e.target.value)}
              placeholder="Ej: juan@email.com"
              disabled={crearMutation.isPending}
            />
          </Field>

          <Field label="Contraseña Temporal" required error={errors.password} name="password">
            <div className="space-y-2">
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  className={`input pr-24 ${errors.password ? "border-rose-300" : ""}`}
                  value={password}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  disabled={crearMutation.isPending}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-20 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  disabled={crearMutation.isPending}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={generarPassword}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-xs bg-slate-100 hover:bg-slate-200 px-2 py-1 rounded transition-colors"
                  disabled={crearMutation.isPending}
                >
                  Generar
                </button>
              </div>

              <p className="text-xs text-slate-500">
                El usuario deberá cambiar esta contraseña en su primer inicio de sesión.
              </p>
            </div>
          </Field>

          <Field label="Rol" required error={errors.rol} name="rol">
            <div className="grid gap-3 md:grid-cols-2">
              <button
                type="button"
                onClick={() => handleRolChange("GESTOR")}
                disabled={crearMutation.isPending}
                className={`text-left rounded-xl border p-4 transition ${
                  rol === "GESTOR"
                    ? "border-slate-900 bg-slate-50 ring-2 ring-slate-200"
                    : "border-slate-200 bg-slate-50 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      rol === "GESTOR" ? "bg-slate-200" : "bg-slate-100"
                    }`}
                  >
                    <UserPlus className="w-5 h-5 text-slate-700" />
                  </div>

                  <div>
                    <p className="font-medium text-slate-900">Gestor</p>
                    <p className="text-sm text-slate-600">
                      Acceso estándar al sistema
                    </p>
                  </div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleRolChange("LECTURA")}
                disabled={crearMutation.isPending}
                className={`text-left rounded-xl border p-4 transition ${
                  rol === "LECTURA"
                    ? "border-slate-900 bg-slate-50 ring-2 ring-slate-200"
                    : "border-slate-200 bg-slate-50 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      rol === "LECTURA" ? "bg-slate-200" : "bg-slate-100"
                    }`}
                  >
                    <BookOpen className="w-5 h-5 text-slate-700" />
                  </div>

                  <div>
                    <p className="font-medium text-slate-900">Lector</p>
                    <p className="text-sm text-slate-600">
                      Solo lectura de la información
                    </p>
                  </div>
                </div>
              </button>
            </div>

            <p className="text-xs text-slate-500 mt-3">
              El administrador del sistema ya está creado. Desde aquí solo podés crear
              usuarios con rol Gestor o Lector.
            </p>
          </Field>

          {crearMutation.isError && (Object.keys(getApiFieldErrors(crearMutation.error)).length === 0 ||
            Object.keys(mapFieldErrors(crearMutation.error, ["nombre", "email", "password", "rol"])).length < Object.keys(getApiFieldErrors(crearMutation.error)).length) && (
            <div role="alert" className="bg-rose-50 text-rose-600 text-sm px-4 py-3 rounded-lg border border-rose-200">
              {getErrorMessage(
                crearMutation.error,
                "Lo sentimos, no pudimos crear el usuario. Verifique los datos e intente nuevamente."
              )}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => nav("/administracion")}
              className="flex-1"
              disabled={crearMutation.isPending}
            >
              Cancelar
            </Button>

            <Button
              type="submit"
              variant="primary"
              disabled={crearMutation.isPending}
              className="flex-1"
            >
              {crearMutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creando...
                </span>
              ) : (
                "Crear Usuario"
              )}
            </Button>
          </div>
        </form>
      </div>
    </section>
  );
}
