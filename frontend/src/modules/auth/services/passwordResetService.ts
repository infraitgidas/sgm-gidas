import { http } from "@/lib/http";
import { normalizeResetEmail } from "@/modules/auth/utils/passwordReset";

type MessageResponse = { data: { message: string }; meta: Record<string, unknown>; error: null };
export type ResetPasswordPayload = { token: string; password_nueva: string; password_confirmacion: string };

export async function requestPasswordReset(email: string): Promise<void> {
  await http<MessageResponse>("/auth/password-reset/request", {
    method: "POST", body: JSON.stringify({ email: normalizeResetEmail(email) }), cache: "no-store",
  }, true);
}

export async function confirmPasswordReset(payload: ResetPasswordPayload): Promise<void> {
  await http<MessageResponse>("/auth/password-reset/confirm", {
    method: "POST", body: JSON.stringify(payload), cache: "no-store",
  }, true);
}

export async function requestAdminPasswordReset(userId: number): Promise<MessageResponse> {
  return http<MessageResponse>(`/auth/usuarios/${userId}/password-reset`, { method: "POST", cache: "no-store" });
}
