import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { FileClock, Lock, LogOut, Shield, User } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Sidebar from "@/components/Sidebar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import { deleteFormDraft, listFormDrafts, type FormDraftSummary } from "@/modules/shared/services/formDraftService";
import RouteBreadcrumbs from "@/modules/shared/components/RouteBreadcrumbs";

export default function AppLayout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isDraftListOpen, setIsDraftListOpen] = useState(false);
  const [draftToDiscard, setDraftToDiscard] = useState<string | null>(null);
  const [deletingDraft, setDeletingDraft] = useState<string | null>(null);
  const [draftActionError, setDraftActionError] = useState("");
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const draftDialogRef = useRef<HTMLDialogElement>(null);
  const { data: drafts = [], isError: draftsError, isFetching: draftsFetching, refetch: refetchDrafts } = useQuery({
    queryKey: ["form-drafts", user?.id],
    queryFn: listFormDrafts,
    enabled: Boolean(user && user.rol !== "LECTURA"),
    refetchOnWindowFocus: "always",
  });

  useEffect(() => {
    if (user && user.rol !== "LECTURA") void refetchDrafts();
  }, [location.pathname, refetchDrafts, user?.id, user?.rol]);

  useEffect(() => {
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!profileMenuRef.current?.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsProfileOpen(false);
    };

    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  useEffect(() => {
    const dialog = draftDialogRef.current;
    if (!dialog || !isDraftListOpen) return;
    dialog.showModal();
    return () => { if (dialog.open) dialog.close(); };
  }, [isDraftListOpen]);

  const discardListedDraft = async (draft: FormDraftSummary) => {
    const draftKey = `${draft.module}:${draft.record_key}`;
    setDeletingDraft(draftKey);
    setDraftActionError("");
    try {
      await deleteFormDraft(draft.module, draft.record_key);
      queryClient.setQueryData<FormDraftSummary[]>(["form-drafts", user?.id], (previous) =>
        previous?.filter((item) => item.module !== draft.module || item.record_key !== draft.record_key)
      );
      setDraftToDiscard(null);
      void refetchDrafts();
    } catch {
      setDraftActionError("No pudimos descartar el borrador. Intente nuevamente.");
    } finally {
      setDeletingDraft(null);
    }
  };

  const roleLabel = isAdmin()
    ? "Administrador"
    : user?.rol === "LECTURA"
      ? "Lector"
      : "Gestor";

  const handleLogout = async () => {
    setIsProfileOpen(false);
    await logout();
  };

  return (
    <div className="min-h-screen bg-[#F6F6FB] text-slate-800 flex flex-col lg:pl-[280px]">
      <a
        href="#main-content"
        onClick={() => document.getElementById("main-content")?.focus()}
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-2 focus:z-[10000] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-sky-800 focus:shadow-lg"
      >
        Saltar al contenido principal
      </a>
      <header className="w-full flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-white h-[56px]">
        <Sidebar />
        <h1 className="font-semibold text-sm tracking-tight"></h1>

        <div ref={profileMenuRef} className="relative">
          <button
            type="button"
            title="Usuario"
            aria-label="Abrir opciones del perfil"
            aria-expanded={isProfileOpen}
            aria-controls="navbar-profile-menu"
            onClick={() => setIsProfileOpen((current) => !current)}
            className="flex items-center justify-center rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          >
            <User aria-hidden="true" className="h-6 w-6" />
          </button>

          {isProfileOpen && (
            <div
              id="navbar-profile-menu"
              className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg"
            >
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {user?.nombre_usuario}
                </p>
                <p className="truncate text-xs text-slate-500">{user?.mail}</p>
                <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-slate-600">
                  {isAdmin() && <Shield aria-hidden="true" className="h-3.5 w-3.5" />}
                  {roleLabel}
                </p>
              </div>

              <nav aria-label="Opciones del perfil" className="p-2 text-sm">
                {user?.rol !== "LECTURA" && (
                  <button
                    type="button"
                    onClick={() => { setIsProfileOpen(false); setIsDraftListOpen(true); void refetchDrafts(); }}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-slate-700 hover:bg-slate-50"
                  >
                    <FileClock aria-hidden="true" className="h-4 w-4" />
                    Borradores {drafts.length > 0 ? `(${drafts.length})` : ""}
                  </button>
                )}
                <NavLink
                  to="/mi-perfil"
                  onClick={() => setIsProfileOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-slate-700 hover:bg-slate-50"
                >
                  <User aria-hidden="true" className="h-4 w-4" />
                  Mi perfil
                </NavLink>
                <NavLink
                  to="/cambiar-password"
                  onClick={() => setIsProfileOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-slate-700 hover:bg-slate-50"
                >
                  <Lock aria-hidden="true" className="h-4 w-4" />
                  Cambiar contraseña
                </NavLink>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-rose-700 hover:bg-rose-50"
                >
                  <LogOut aria-hidden="true" className="h-4 w-4" />
                  Cerrar sesión
                </button>
              </nav>
            </div>
          )}
        </div>
      </header>

      {isDraftListOpen && (
        <dialog ref={draftDialogRef} onCancel={() => setIsDraftListOpen(false)} aria-labelledby="draft-list-title" className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl backdrop:bg-slate-950/50">
            <h2 id="draft-list-title" className="text-lg font-semibold">Tus borradores</h2>
            <p className="mt-1 text-sm text-slate-600">Cada elemento conserva solo su último borrador durante siete días.</p>
            {draftsFetching && <p role="status" className="mt-4 text-sm text-slate-600">Actualizando borradores...</p>}
            {draftsError && <p role="alert" className="mt-4 text-sm text-rose-700">No pudimos recuperar los borradores. Intente nuevamente.</p>}
            {!draftsFetching && !draftsError && drafts.length === 0 && <p className="mt-4 text-sm text-slate-600">No hay borradores activos.</p>}
            {!draftsFetching && !draftsError && <ul className="mt-4 max-h-80 space-y-2 overflow-y-auto">
              {drafts.map((draft) => (
                <li key={`${draft.module}:${draft.record_key}`} className="rounded-lg border border-slate-200 p-3">
                  <button type="button" className="w-full text-left hover:text-sky-800" disabled={Boolean(deletingDraft)} onClick={() => { setIsDraftListOpen(false); navigate(draft.path); }}>
                    <span className="block font-medium">{draft.label}{draft.display_name ? `: ${draft.display_name}` : ""}</span>
                    <span className="block text-xs text-slate-600">{draft.record_key === "new" ? "Alta nueva" : `Registro #${draft.record_key}`} · Guardado el {new Date(draft.saved_at).toLocaleString("es-AR")}</span>
                  </button>
                  {draftToDiscard === `${draft.module}:${draft.record_key}` ? (
                    <div className="mt-3 border-t border-slate-200 pt-3 text-sm">
                      <p>¿Descartar este borrador?</p>
                      <div className="mt-2 flex flex-wrap gap-3">
                        <button type="button" className="font-medium text-rose-700 hover:underline" disabled={Boolean(deletingDraft)} onClick={() => void discardListedDraft(draft)}>Confirmar descarte</button>
                        <button type="button" className="text-slate-600 hover:underline" disabled={Boolean(deletingDraft)} onClick={() => setDraftToDiscard(null)}>Cancelar</button>
                      </div>
                    </div>
                  ) : (
                    <button type="button" className="mt-2 text-sm text-rose-700 hover:underline" disabled={Boolean(deletingDraft)} onClick={() => { setDraftActionError(""); setDraftToDiscard(`${draft.module}:${draft.record_key}`); }}>Descartar borrador</button>
                  )}
                </li>
              ))}
            </ul>}
            {draftActionError && <p role="alert" className="mt-3 text-sm text-rose-700">{draftActionError}</p>}
            <div className="mt-5 flex justify-end gap-2">
              {draftsError && <button type="button" className="rounded-lg px-3 py-2 text-sm text-sky-700" onClick={() => void refetchDrafts()}>Reintentar</button>}
              <button type="button" className="rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" onClick={() => setIsDraftListOpen(false)}>Cerrar</button>
            </div>
        </dialog>
      )}

      <main id="main-content" tabIndex={-1} className="flex-1">
        <div className="w-full max-w-7xl mx-auto px-6 lg:px-10 py-4">
          <RouteBreadcrumbs />
          {drafts.length > 0 && (
            <div role="status" className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
              <span>{drafts.length === 1 ? "Tiene 1 borrador activo." : `Tiene ${drafts.length} borradores activos.`}</span>
              <button type="button" className="font-semibold underline underline-offset-2" onClick={() => { setIsDraftListOpen(true); void refetchDrafts(); }}>Consultar la lista</button>
            </div>
          )}
          <Outlet />
        </div>
      </main>

      <Footer />
    </div>
  );
}
