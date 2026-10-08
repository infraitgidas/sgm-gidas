import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  actualizarUsuario,
  eliminarUsuario,
  getUsuarios,
  rolToRolId,
  type ActualizarUsuarioPayload,
  type Usuario,
  type UsuarioRol,
} from "@/modules/auth/services/usuariosService";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage } from "@/lib/httpError";
import Button from "@/components/Button";
import type { Rol } from "@/modules/auth/services/authService";
import {
  Users,
  Trash2,
  Edit3,
  AlertCircle,
  X,
  Shield,
  UserCog,
  BookOpen,
  Loader2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

function normalizeRolForForm(rol: UsuarioRol): Rol {
  return rol;
}

function isSameRol(a: UsuarioRol, b: Rol) {
  return normalizeRolForForm(a) === b;
}

function getRolConfig(rol: string) {
  switch (rol) {
    case "ADMIN":
      return {
        label: "Administrador",
        icon: Shield,
        className: "bg-violet-100 text-violet-700 border border-violet-200",
        iconClassName: "text-violet-700",
      };

    case "LECTURA":
      return {
        label: "Lector",
        icon: BookOpen,
        className: "bg-amber-100 text-amber-700 border border-amber-200",
        iconClassName: "text-amber-700",
      };

    case "GESTOR":
    default:
      return {
        label: "Gestor",
        icon: UserCog,
        className: "bg-sky-100 text-sky-700 border border-sky-200",
        iconClassName: "text-sky-700",
      };
  }
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidUsername(username: string): boolean {
  return /^[a-zA-Z0-9._-]+$/.test(username);
}

export default function UsuariosHome() {
  const { isAdmin, user } = useAuth();
  const nav = useNavigate();
  const queryClient = useQueryClient();

  const [usuarioAEliminar, setUsuarioAEliminar] = useState<Usuario | null>(null);
  const editDialogRef = useRef<HTMLDialogElement>(null);
  const deleteDialogRef = useRef<HTMLDialogElement>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [usuarioAEditar, setUsuarioAEditar] = useState<Usuario | null>(null);
  const [editForm, setEditForm] = useState({
    nombre_usuario: "",
    mail: "",
    rol: "GESTOR" as Rol,
  });
  const [editErrors, setEditErrors] = useState<{
    nombre_usuario?: string;
    mail?: string;
    rol?: string;
    general?: string;
  }>({});

  useEffect(() => {
    const dialog = editDialogRef.current;
    if (!usuarioAEditar || !dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    dialog.querySelector<HTMLElement>("input")?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (opener?.isConnected) opener.focus();
    };
  }, [usuarioAEditar]);

  useEffect(() => {
    const dialog = deleteDialogRef.current;
    if (!usuarioAEliminar || !dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    dialog.querySelector<HTMLElement>("button")?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (opener?.isConnected) opener.focus();
    };
  }, [usuarioAEliminar]);

  if (!isAdmin()) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-16 h-16 text-slate-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Acceso Denegado</h2>
        <p className="text-slate-500">No tienes permisos para gestionar usuarios.</p>
      </div>
    );
  }

  const { data: usuarios, isLoading, error } = useQuery({
    queryKey: ["usuarios"],
    queryFn: getUsuarios,
  });

  const eliminarMutation = useMutation({
    mutationFn: eliminarUsuario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usuarios"] });
      setUsuarioAEliminar(null);
      setDeleteError(null);
    },
    onError: (error) => {
      setDeleteError(getErrorMessage(error, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
    },
  });

  const editarMutation = useMutation({
    mutationFn: (payload: {
      id: number;
      data: ActualizarUsuarioPayload;
    }) => actualizarUsuario(payload.id, payload.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usuarios"] });
      setUsuarioAEditar(null);
      setEditErrors({});
    },
    onError: (error) => {
      setEditErrors((prev) => ({
        ...prev,
        general: getErrorMessage(error, "Lo sentimos, no pudimos guardar los cambios. Verifique los datos e intente nuevamente."),
      }));
    },
  });

  function handleEliminar(usuario: Usuario) {
    setUsuarioAEliminar(usuario);
    setDeleteError(null);
  }

  function handleEditar(usuario: Usuario) {
    setUsuarioAEditar(usuario);
    setEditForm({
      nombre_usuario: usuario.nombre_usuario,
      mail: usuario.mail,
      rol: normalizeRolForForm(usuario.rol),
    });
    setEditErrors({});
    editarMutation.reset();
  }

  function handleCerrarModal() {
    setUsuarioAEliminar(null);
    setDeleteError(null);
    eliminarMutation.reset();
  }

  function handleCerrarEditar() {
    setUsuarioAEditar(null);
    setEditErrors({});
    editarMutation.reset();
  }

  function validarEdicion() {
    const errors: typeof editErrors = {};
    const nombreUsuario = editForm.nombre_usuario.trim();
    const mail = editForm.mail.trim();

    if (!nombreUsuario) {
      errors.nombre_usuario = "El nombre de usuario es obligatorio";
    } else if (nombreUsuario.length < 3) {
      errors.nombre_usuario = "El nombre debe tener al menos 3 caracteres";
    } else if (!isValidUsername(nombreUsuario)) {
      errors.nombre_usuario = "Solo letras, números, puntos, guiones y guiones bajos";
    }

    if (!mail) {
      errors.mail = "El email es obligatorio";
    } else if (!isValidEmail(mail)) {
      errors.mail = "Ingrese un email valido";
    }

    if (!["ADMIN", "GESTOR", "LECTURA"].includes(editForm.rol)) {
      errors.rol = "Debe seleccionar un rol valido";
    }

    if (
      usuarioAEditar &&
      usuarioAEditar.id === user?.id &&
      !isSameRol(usuarioAEditar.rol, editForm.rol)
    ) {
      errors.rol = "No puede cambiar el rol de su propia cuenta";
    }

    setEditErrors(errors);
    const firstInvalidField = errors.nombre_usuario
      ? "editar-usuario-nombre"
      : errors.mail
        ? "editar-usuario-email"
        : errors.rol
          ? "editar-usuario-rol"
          : null;
    if (firstInvalidField) {
      window.requestAnimationFrame(() => {
        document.getElementById(firstInvalidField)?.focus();
      });
    }
    return Object.keys(errors).length === 0;
  }

  function confirmarEdicion() {
    if (!usuarioAEditar || !validarEdicion()) return;

    const data: ActualizarUsuarioPayload = {};
    const nombreUsuario = editForm.nombre_usuario.trim();
    const mail = editForm.mail.trim();

    if (nombreUsuario !== usuarioAEditar.nombre_usuario) {
      data.nombre_usuario = nombreUsuario;
    }

    if (mail !== usuarioAEditar.mail) {
      data.mail = mail;
    }

    if (!isSameRol(usuarioAEditar.rol, editForm.rol)) {
      data.rol_id = rolToRolId(editForm.rol);
    }

    if (Object.keys(data).length === 0) {
      handleCerrarEditar();
      return;
    }

    editarMutation.mutate({
      id: usuarioAEditar.id,
      data,
    });
  }

  function confirmarEliminar() {
    if (!usuarioAEliminar) return;
    setDeleteError(null);
    eliminarMutation.mutate(usuarioAEliminar.id);
  }

  const total = usuarios?.length || 0;
  const admins = usuarios?.filter((u) => u.rol === "ADMIN").length || 0;
  const gestores = usuarios?.filter((u) => u.rol === "GESTOR").length || 0;
  const lectores = usuarios?.filter((u) => u.rol === "LECTURA").length || 0;

  return (
    <section className="w-full">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl md:text-3xl font-semibold leading-none">
          Gestión de Usuarios
        </h2>
        <Button variant="secondary" size="sm" onClick={() => nav("/administracion")}>
          Volver a Administración
        </Button>
      </div>

      <div className="mt-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-100 rounded-lg">
            <Users className="w-6 h-6 text-slate-700" />
          </div>
          <div>
            <p className="text-sm text-slate-600">
              {total} usuario{total !== 1 ? "s" : ""} registrado{total !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/70 flex items-center justify-center">
              <Shield className="w-5 h-5 text-violet-700" />
            </div>
            <div>
              <p className="text-sm text-violet-700">Administradores</p>
              <p className="text-2xl font-semibold text-violet-900">{admins}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/70 flex items-center justify-center">
              <UserCog className="w-5 h-5 text-sky-700" />
            </div>
            <div>
              <p className="text-sm text-sky-700">Gestores</p>
              <p className="text-2xl font-semibold text-sky-900">{gestores}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/70 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-amber-700" />
            </div>
            <div>
              <p className="text-sm text-amber-700">Lectores</p>
              <p className="text-2xl font-semibold text-amber-900">{lectores}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-pulse space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-slate-200 rounded-full"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 bg-slate-200 rounded"></div>
                    <div className="h-3 w-48 bg-slate-100 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-600">
            {getErrorMessage(error, "Lo sentimos, no pudimos recuperar la información. Intente nuevamente.")}
          </div>
        ) : !usuarios || usuarios.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">No hay usuarios registrados</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">
                    Usuario
                  </th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">
                    Email
                  </th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">
                    Rol
                  </th>
                  <th className="text-left px-6 py-4 text-sm font-semibold text-slate-700">
                    Estado
                  </th>
                  <th className="text-right px-6 py-4 text-sm font-semibold text-slate-700">
                    Acciones
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {usuarios.map((usuarioItem) => {
                  const rolConfig = getRolConfig(usuarioItem.rol);
                  const RolIcon = rolConfig.icon;
                  const esUsuarioActual = user?.id === usuarioItem.id;

                  return (
                    <tr key={usuarioItem.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-slate-900">
                              {usuarioItem.nombre_usuario}
                            </p>

                            {esUsuarioActual && (
                              <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                                Vos
                              </span>
                            )}
                          </div>

                          <p className="text-xs text-slate-500">
                            ID: {usuarioItem.id}
                          </p>
                        </div>
                      </td>

                      <td className="px-6 py-4 text-slate-600">
                        {usuarioItem.mail}
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${rolConfig.className}`}
                        >
                          <RolIcon className={`w-3.5 h-3.5 ${rolConfig.iconClassName}`} />
                          {rolConfig.label}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 text-xs ${
                            usuarioItem.activo ? "text-green-600" : "text-slate-400"
                          }`}
                        >
                          <span
                            className={`w-2 h-2 rounded-full ${
                              usuarioItem.activo ? "bg-green-500" : "bg-slate-300"
                            }`}
                          />
                          {usuarioItem.activo ? "Activo" : "Inactivo"}
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleEditar(usuarioItem)}
                            className="p-2 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
                            title="Editar usuario"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>

                          <button
                            onClick={() => handleEliminar(usuarioItem)}
                            className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                            title={
                              esUsuarioActual
                                ? "Eliminar tu usuario"
                                : "Eliminar usuario"
                            }
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {usuarioAEditar && (
        <dialog ref={editDialogRef} aria-labelledby="editar-usuario-title" onCancel={(event) => { event.preventDefault(); if (!editarMutation.isPending) handleCerrarEditar(); }} className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-lg rounded-2xl p-0 shadow-xl backdrop:bg-black/50">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 id="editar-usuario-title" className="text-lg font-semibold">Editar usuario</h3>
              <button
                onClick={handleCerrarEditar}
                className="p-1 hover:bg-slate-100 rounded"
                disabled={editarMutation.isPending}
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="editar-usuario-nombre" className="mb-2 block text-sm font-medium">
                  Nombre de usuario
                </label>
                <input
                  id="editar-usuario-nombre"
                  type="text"
                  aria-invalid={Boolean(editErrors.nombre_usuario)}
                  aria-describedby={editErrors.nombre_usuario ? "editar-usuario-nombre-error" : undefined}
                  className={`input ${editErrors.nombre_usuario ? "border-rose-300" : ""}`}
                  value={editForm.nombre_usuario}
                  onChange={(event) => {
                    setEditForm((prev) => ({
                      ...prev,
                      nombre_usuario: event.target.value,
                    }));
                    if (editErrors.nombre_usuario) {
                      setEditErrors((prev) => ({
                        ...prev,
                        nombre_usuario: undefined,
                        general: undefined,
                      }));
                    }
                  }}
                  disabled={editarMutation.isPending}
                />
                {editErrors.nombre_usuario && (
                  <p id="editar-usuario-nombre-error" role="alert" className="mt-1 text-sm text-rose-600">
                    {editErrors.nombre_usuario}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="editar-usuario-email" className="mb-2 block text-sm font-medium">Email</label>
                <input
                  id="editar-usuario-email"
                  type="email"
                  aria-invalid={Boolean(editErrors.mail)}
                  aria-describedby={editErrors.mail ? "editar-usuario-email-error" : undefined}
                  className={`input ${editErrors.mail ? "border-rose-300" : ""}`}
                  value={editForm.mail}
                  onChange={(event) => {
                    setEditForm((prev) => ({
                      ...prev,
                      mail: event.target.value,
                    }));
                    if (editErrors.mail) {
                      setEditErrors((prev) => ({
                        ...prev,
                        mail: undefined,
                        general: undefined,
                      }));
                    }
                  }}
                  disabled={editarMutation.isPending}
                />
                {editErrors.mail && (
                  <p id="editar-usuario-email-error" role="alert" className="mt-1 text-sm text-rose-600">{editErrors.mail}</p>
                )}
              </div>

              <div>
                <label htmlFor="editar-usuario-rol" className="mb-2 block text-sm font-medium">Rol</label>
                {usuarioAEditar.id === user?.id ? (
                  <input
                    id="editar-usuario-rol"
                    type="text"
                    readOnly
                    value={getRolConfig(editForm.rol).label}
                    aria-invalid={Boolean(editErrors.rol)}
                    aria-describedby={editErrors.rol
                      ? "editar-usuario-rol-ayuda editar-usuario-rol-error"
                      : "editar-usuario-rol-ayuda"}
                    className={`input ${editErrors.rol ? "border-rose-300" : ""}`}
                  />
                ) : (
                  <select
                    id="editar-usuario-rol"
                    aria-invalid={Boolean(editErrors.rol)}
                    aria-describedby={editErrors.rol ? "editar-usuario-rol-error" : undefined}
                    className={`input ${editErrors.rol ? "border-rose-300" : ""}`}
                    value={editForm.rol}
                    onChange={(event) => {
                      setEditForm((prev) => ({
                        ...prev,
                        rol: event.target.value as Rol,
                      }));
                      if (editErrors.rol) {
                        setEditErrors((prev) => ({
                          ...prev,
                          rol: undefined,
                          general: undefined,
                        }));
                      }
                    }}
                    disabled={editarMutation.isPending}
                  >
                    <option value="ADMIN">Administrador</option>
                    <option value="GESTOR">Gestor</option>
                    <option value="LECTURA">Lector</option>
                  </select>
                )}
                {usuarioAEditar.id === user?.id && (
                  <p id="editar-usuario-rol-ayuda" className="mt-1 text-xs text-slate-500">
                    No puede modificar el rol de su propia cuenta.
                  </p>
                )}
                {editErrors.rol && (
                  <p id="editar-usuario-rol-error" role="alert" className="mt-1 text-sm text-rose-600">{editErrors.rol}</p>
                )}
              </div>

              {editErrors.general && (
                <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {editErrors.general}
                </div>
              )}
            </div>

            <div className="mt-6 flex gap-3">
              <Button
                variant="secondary"
                onClick={handleCerrarEditar}
                className="flex-1"
                disabled={editarMutation.isPending}
              >
                Cancelar
              </Button>

              <Button
                variant="primary"
                onClick={confirmarEdicion}
                className="flex-1"
                disabled={editarMutation.isPending}
              >
                {editarMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Guardando...
                  </span>
                ) : (
                  "Guardar cambios"
                )}
              </Button>
            </div>
          </div>
        </dialog>
      )}

      {usuarioAEliminar && (
        <dialog ref={deleteDialogRef} aria-labelledby="eliminar-usuario-title" aria-describedby="eliminar-usuario-description" onCancel={(event) => { event.preventDefault(); if (!eliminarMutation.isPending) handleCerrarModal(); }} className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl p-0 shadow-xl backdrop:bg-black/50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 id="eliminar-usuario-title" className="text-lg font-semibold">¿Eliminar usuario?</h3>
              <button
                onClick={handleCerrarModal}
                className="p-1 hover:bg-slate-100 rounded"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <p id="eliminar-usuario-description" className="text-slate-600 mb-6">
              Estás a punto de eliminar al usuario{" "}
              <strong>{usuarioAEliminar.nombre_usuario}</strong>.
            </p>

            {deleteError && (
              <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {deleteError}
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={handleCerrarModal}
                className="flex-1"
              >
                Cancelar
              </Button>

              <Button
                variant="primary"
                onClick={confirmarEliminar}
                className="flex-1 bg-rose-600 hover:bg-rose-700"
                disabled={eliminarMutation.isPending}
              >
                {eliminarMutation.isPending ? "Eliminando..." : "Eliminar"}
              </Button>
            </div>
          </div>
        </dialog>
      )}
    </section>
  );
}
