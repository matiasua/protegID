import { ApiRequestError } from "@/lib/api";
import type { AuthUser } from "@/types/auth";

export function isEmailVerified(user: AuthUser | null): boolean {
  return user?.email_verified_at !== null && user?.email_verified_at !== undefined;
}

export function getResendVerificationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }

  return "No se pudo reenviar el correo de verificación.";
}
