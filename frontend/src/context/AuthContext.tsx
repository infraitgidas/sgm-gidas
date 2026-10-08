import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
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
import { clearAccessToken } from "@/lib/http";
import SessionExpiryDialog from "@/modules/auth/components/SessionExpiryDialog";
import { useSessionLifecycle } from "@/modules/auth/hooks/useSessionLifecycle";
import { clearSessionNotice, markSessionActive, markSessionEnded, rememberSessionPath } from "@/modules/auth/utils/sessionNavigation";
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
  const [sessionTiming, setSessionTiming] = useState<SessionTiming | null>(null);

  const clearSession = useCallback((rememberPath = false) => {
    if (rememberPath) {
      rememberSessionPath(
        `${window.location.pathname}${window.location.search}${window.location.hash}`
      );
    }
    clearAccessToken();
    queryClient.clear();
    setUser(null);
    setToken(null);
    setSessionTiming(null);
  }, [queryClient]);

  const expireSession = useCallback(() => {
    markSessionEnded();
    clearSession(true);
  }, [clearSession]);

  const renewSession = useCallback(async () => {
    const auth = await renewSessionService();
    if (!auth) return false;
    setUser(auth.user);
    setToken(auth.token);
    setSessionTiming(auth.sessionTiming);
    markSessionActive();
    return true;
  }, []);

  const sessionLifecycle = useSessionLifecycle({
    timing: user ? sessionTiming : null,
    onRefresh: renewSession,
    onExpire: expireSession,
  });

  useEffect(() => {
    let active = true;

    async function initializeSession() {
      setLoading(true);
      try {
        const stored = await restoreSession();
        if (!active) return;
        setUser(stored?.user ?? null);
        setToken(stored?.token ?? null);
        setSessionTiming(stored?.sessionTiming ?? null);
        if (stored) markSessionActive();
        else markSessionEnded();
      } catch {
        if (!active) return;
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
    markSessionActive();
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
    markSessionActive();
  }

  async function logout() {
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
      {children}
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
