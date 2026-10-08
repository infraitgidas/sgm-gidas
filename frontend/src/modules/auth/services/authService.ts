import {
  HttpError,
  clearAccessToken,
  http,
  refreshSession,
  setAccessToken,
  withAuthCookieLock,
} from "@/lib/http";
import type { SessionTiming } from "@/modules/auth/utils/sessionTiming";

export type Rol = "ADMIN" | "GESTOR" | "LECTURA";

export type User = {
  id: number;
  nombre_usuario: string;
  mail: string;
  rol: Rol;
  primer_login: boolean;
  activo?: boolean;
};

export type AuthResponse = {
  user: User;
  token: string;
  sessionTiming: SessionTiming;
};

type BackendLoginResponse = {
  access_token: string;
  access_expires_at: string;
  session_expires_at: string;
  session_warning_seconds: number;
  user?: User;
  usuario?: User;
};

const AUTH_CHANNEL = "gidas_auth_events";
const LEGACY_AUTH_KEY = "gidas_auth_current_session";
const CONNECTION_ERROR_MESSAGE =
  "Lo sentimos, no pudimos conectar con el servidor. Intente nuevamente en unos minutos.";

export async function restoreSession(): Promise<AuthResponse | null> {
  removeLegacyAuthStorage();
  const response = await refreshSession<User>();
  const user = response?.user ?? response?.usuario;
  if (!response?.access_token || !user) return null;

  return toAuthResponse(response, user);
}

export async function login(
  usuario: string,
  password: string
): Promise<AuthResponse> {
  let responseBack: BackendLoginResponse;

  try {
    responseBack = await http<BackendLoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        nombre_usuario: usuario,
        password,
      }),
    }, true);
  } catch (error) {
    if (error instanceof HttpError) throw error;
    throw new Error(CONNECTION_ERROR_MESSAGE);
  }

  const auth = toAuthResponse(responseBack, responseBack.user ?? responseBack.usuario!);

  if (!auth.user || !auth.token) {
    clearAccessToken();
    throw new Error(CONNECTION_ERROR_MESSAGE);
  }

  setAccessToken(auth.token);
  return auth;
}

export async function renewSession(): Promise<AuthResponse | null> {
  const response = await refreshSession<User>();
  const user = response?.user ?? response?.usuario;
  if (!response?.access_token || !user) return null;
  return toAuthResponse(response, user);
}

function toAuthResponse(
  response: BackendLoginResponse,
  user: User
): AuthResponse {
  return {
    user,
    token: response.access_token,
    sessionTiming: {
      accessExpiresAt: response.access_expires_at,
      sessionExpiresAt: response.session_expires_at,
      warningSeconds: response.session_warning_seconds,
    },
  };
}

export async function register(
  usuario: string,
  email: string,
  password: string
): Promise<void> {
  await http("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      nombre_usuario: usuario,
      mail: email,
      password,
    }),
  });
}

export async function esPrimerUsuario(): Promise<boolean> {
  const response = await http<{ existe: boolean }>("/auth/primer-usuario", {
    method: "GET",
  });
  return !response.existe;
}

type CambiarPasswordParams = {
  passwordNueva: string;
  passwordActual?: string;
};

export async function cambiarPassword({
  passwordNueva,
  passwordActual,
}: CambiarPasswordParams): Promise<AuthResponse> {
  const body: Record<string, string> = {
    password_nueva: passwordNueva,
    password_confirmacion: passwordNueva,
  };

  if (passwordActual?.trim()) {
    body.password_actual = passwordActual;
  }

  try {
    const response = await http<BackendLoginResponse>("/auth/cambiar-password", {
      method: "POST",
      body: JSON.stringify(body),
    });
    const user = response.user ?? response.usuario;
    if (!response.access_token || !user) throw new Error(CONNECTION_ERROR_MESSAGE);
    const auth = toAuthResponse(response, user);
    setAccessToken(auth.token);
    return auth;
  } catch (error) {
    if (error instanceof HttpError) {
      throw error;
    }

    throw new Error(CONNECTION_ERROR_MESSAGE);
  }
}

export async function logout(): Promise<void> {
  clearAccessToken();
  publishAuthEvent("logout");

  try {
    await withAuthCookieLock(() =>
      http(
        "/auth/logout",
        {
          method: "POST",
        },
        true
      )
    );
  } catch {
    // La limpieza local debe completarse aunque la sesion ya haya expirado.
  }
}

export function subscribeToAuthEvents(onLogout: () => void): () => void {
  if (!("BroadcastChannel" in window)) return () => undefined;

  const channel = new BroadcastChannel(AUTH_CHANNEL);
  channel.addEventListener("message", (event: MessageEvent<unknown>) => {
    if (event.data === "logout") onLogout();
  });

  return () => channel.close();
}

function publishAuthEvent(event: "logout") {
  if (!("BroadcastChannel" in window)) return;

  const channel = new BroadcastChannel(AUTH_CHANNEL);
  channel.postMessage(event);
  channel.close();
}

function removeLegacyAuthStorage() {
  localStorage.removeItem(LEGACY_AUTH_KEY);
  sessionStorage.removeItem(LEGACY_AUTH_KEY);
}
