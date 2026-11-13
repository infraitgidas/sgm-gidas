import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  useRef,
  ReactNode,
} from "react";
import {
  login as loginService,
  register as registerService,
  logout as logoutService,
  restoreSession,
  renewSession as renewSessionService,
  subscribeToAuthEvents,
  esPrimerUsuario as esPrimerUsuarioService,
  cambiarPassword as cambiarPasswordService,
  type User,
  type Rol,
  type AuthResponse,
} from "@/modules/auth/services/authService";
import { clearAccessToken, type RefreshSessionResponse } from "@/lib/http";
import SessionExpiryDialog from "@/modules/auth/components/SessionExpiryDialog";
import { useSessionLifecycle } from "@/modules/auth/hooks/useSessionLifecycle";
import { clearSessionNotice, markSessionActive, markSessionEnded, rememberSessionPath } from "@/modules/auth/utils/sessionNavigation";
import { writeSharedTiming, readNewerTiming, clearSharedTiming } from "@/modules/auth/utils/sharedSessionTiming";
import type { SessionTiming } from "@/modules/auth/utils/sessionTiming";
import { useQueryClient } from "@tanstack/react-query";

type AuthContextValue = {
  user: User | null;
  token: string | null;
  loading: boolean;

  login: (usuario: string, password: string) => Promise<AuthResponse>;
  register: (nombre: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  esPrimerUsuario: () => Promise<boolean>;
  cambiarPassword: (params: {
    passwordNueva: string;
    passwordActual?: string;
  }) => Promise<void>;

  isAdmin: () => boolean;
  isGestor: () => boolean;
  isLector: () => boolean;

  debeCambiarPassword: () => boolean;

  canManageUsers: () => boolean;
  canCreateRecords: () => boolean;
  canEditRecords: () => boolean;
  canDeleteRecords: () => boolean;
  canReadRecords: () => boolean;
  canEditOwnProfile: () => boolean;

  updateUserInSession: (partial: Partial<User>) => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [restoreError, setRestoreError] = useState(false);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const [sessionTiming, setSessionTiming] = useState<SessionTiming | null>(null);

  const currentUserId = useRef<number | undefined>(undefined);
  currentUserId.current = user?.id;

  const clearSession = useCallback((rememberPath = false) => {
    if (rememberPath) {
      rememberSessionPath(
        `${window.location.pathname}${window.location.search}${window.location.hash}`,
        sessionStorage,
        window.history.state?.usr,
        currentUserId.current,
      );
    }
    clearAccessToken();
    queryClient.clear();
    setUser(null);
    setToken(null);
    setSessionTiming(null);
  }, [queryClient]);

  const expireSession = useCallback(() => {
    if (currentUserId.current) clearSharedTiming(currentUserId.current);
    markSessionEnded();
    clearSession(true);
  }, [clearSession]);

  const renewSession = useCallback(async () => {
    const auth = await renewSessionService();
    if (!auth) return false;
    setUser(auth.user);
    setToken(auth.token);
    setSessionTiming(auth.sessionTiming);
    writeSharedTiming(auth.user.id, auth.sessionTiming);
    markSessionActive(sessionStorage, auth.user.id);
    return true;
  }, []);

  const sessionLifecycle = useSessionLifecycle({
    timing: user ? sessionTiming : null,
    onRefresh: renewSession,
    onExpire: expireSession,
    getLatestTiming: () => {
      if (!user || !sessionTiming) return sessionTiming;
      const latest = readNewerTiming(user.id, sessionTiming);
      if (latest !== sessionTiming) setSessionTiming(latest);
      return latest;
    },
  });

  useEffect(() => {
    let active = true;

    async function initializeSession() {
      setLoading(true);
      setRestoreError(false);
      try {
        const stored = await restoreSession();
        if (!active) return;
        setUser(stored?.user ?? null);
        setToken(stored?.token ?? null);
        setSessionTiming(stored?.sessionTiming ?? null);
        if (stored) markSessionActive(sessionStorage, stored.user.id);
        else markSessionEnded();
      } catch {
        if (!active) return;
        setRestoreError(true);
        clearAccessToken();
        setUser(null);
        setToken(null);
        setSessionTiming(null);
      } finally {
        if (active) setLoading(false);
      }
    }

    void initializeSession();

    return () => {
      active = false;
    };
  }, [restoreAttempt]);

  useEffect(() => {
    const channel = typeof BroadcastChannel !== "undefined"
      ? new BroadcastChannel("gidas_session_timing") : null;
    const acceptTiming = (data: SessionTiming) => {
      if (Number.isFinite(Date.parse(data?.sessionExpiresAt)) &&
          Number.isFinite(Date.parse(data?.accessExpiresAt)) &&
          Number.isFinite(data?.warningSeconds)) {
        setSessionTiming(data);
      }
    };
    if (channel) channel.onmessage = event => {
      if (event.data?.userId === currentUserId.current) acceptTiming(event.data.timing);
    };
    const handleRenewed = (event: Event) => {
      const data = (event as CustomEvent<RefreshSessionResponse<User>>).detail;
      const timing = {
        accessExpiresAt: data.access_expires_at,
        sessionExpiresAt: data.session_expires_at,
        warningSeconds: data.session_warning_seconds,
      };
      const userId = data.user?.id ?? data.usuario?.id;
      if (userId) writeSharedTiming(userId, timing);
      acceptTiming(timing);
      channel?.postMessage({ userId, timing });
    };
    window.addEventListener("gidas:session-renewed", handleRenewed);
    return () => {
      window.removeEventListener("gidas:session-renewed", handleRenewed);
      channel?.close();
    };
  }, []);

  useEffect(() => {
    const handleRemoteLogout = () => clearSession(false);
    const handleExpired = () => expireSession();
    const unsubscribe = subscribeToAuthEvents(handleRemoteLogout);
    window.addEventListener("gidas:session-expired", handleExpired);

    return () => {
      unsubscribe();
      window.removeEventListener("gidas:session-expired", handleExpired);
    };
  }, [clearSession, expireSession]);

  function updateUserInSession(partial: Partial<User>) {
    if (!user) return;
    setUser({ ...user, ...partial });
  }

  async function login(usuario: string, password: string): Promise<AuthResponse> {
    const auth = await loginService(usuario, password);
    queryClient.clear();
    setUser(auth.user);
    setToken(auth.token);
    setSessionTiming(auth.sessionTiming);
    writeSharedTiming(auth.user.id, auth.sessionTiming);
    markSessionActive(sessionStorage, auth.user.id);
    return auth;
  }

  async function register(nombre: string, email: string, password: string) {
    await registerService(nombre, email, password);
  }

  async function esPrimerUsuario() {
    return esPrimerUsuarioService();
  }

  async function cambiarPassword({
    passwordNueva,
    passwordActual,
  }: {
    passwordNueva: string;
    passwordActual?: string;
  }) {
    const auth = await cambiarPasswordService({ passwordNueva, passwordActual });
    setUser(auth.user);
    setToken(auth.token);
    setSessionTiming(auth.sessionTiming);
    writeSharedTiming(auth.user.id, auth.sessionTiming);
    markSessionActive(sessionStorage, auth.user.id);
  }

  async function logout() {
    if (user) clearSharedTiming(user.id);
    clearSessionNotice();
    queryClient.clear();
    setUser(null);
    setToken(null);
    setSessionTiming(null);
    await logoutService();
  }

  function isAdmin(): boolean {
    return user?.rol === "ADMIN";
  }

  function isGestor(): boolean {
    return user?.rol === "GESTOR";
  }

  function isLector(): boolean {
    return user?.rol === "LECTURA";
  }

  function debeCambiarPassword(): boolean {
    return user?.primer_login === true;
  }

  function canManageUsers(): boolean {
    return isAdmin();
  }

  function canCreateRecords(): boolean {
    return isAdmin() || isGestor();
  }

  function canEditRecords(): boolean {
    return isAdmin() || isGestor();
  }

  function canDeleteRecords(): boolean {
    return isAdmin() || isGestor();
  }

  function canReadRecords(): boolean {
    return !!user;
  }

  function canEditOwnProfile(): boolean {
    return !!user;
  }

  const value: AuthContextValue = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    esPrimerUsuario,
    cambiarPassword,

    isAdmin,
    isGestor,
    isLector,

    debeCambiarPassword,

    canManageUsers,
    canCreateRecords,
    canEditRecords,
    canDeleteRecords,
    canReadRecords,
    canEditOwnProfile,

    updateUserInSession,
  };

  return (
    <AuthContext.Provider value={value}>
      {restoreError ? (
        <div role="alert" className="mx-auto my-16 max-w-md rounded-xl border bg-white p-6 text-slate-800">
          <p>Lo sentimos, no pudimos recuperar su sesión. Verifique la conexión e intente nuevamente.</p>
          <button type="button" className="mt-4 rounded bg-blue-700 px-4 py-2 text-white focus-visible:outline" onClick={() => setRestoreAttempt(value => value + 1)}>
            Reintentar
          </button>
        </div>
      ) : children}
      <SessionExpiryDialog
        open={sessionLifecycle.warningOpen}
        remainingSeconds={sessionLifecycle.remainingSeconds}
        extending={sessionLifecycle.extending}
        error={sessionLifecycle.extensionError}
        onContinue={() => void sessionLifecycle.extendSession()}
        onLogout={() => void logout()}
      />
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
