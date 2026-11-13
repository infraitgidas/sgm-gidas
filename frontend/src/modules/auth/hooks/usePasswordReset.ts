import { useMutation } from "@tanstack/react-query";
import { confirmPasswordReset, requestAdminPasswordReset, requestPasswordReset } from "@/modules/auth/services/passwordResetService";

export function useRequestPasswordReset() { return useMutation({ mutationFn: requestPasswordReset }); }
export function useConfirmPasswordReset() { return useMutation({ mutationFn: confirmPasswordReset }); }
export function useAdminPasswordReset() { return useMutation({ mutationFn: requestAdminPasswordReset }); }
