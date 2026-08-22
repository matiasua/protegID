"use client";

import { Button } from "@/components/ui/button";
import { isEmailVerified } from "@/components/dashboard/account/types";
import { useResendVerification } from "@/components/dashboard/account/use-resend-verification";
import type { AuthUser } from "@/types/auth";

export interface EmailVerificationBannerProps {
  currentUser: AuthUser | null;
}

export function EmailVerificationBanner({ currentUser }: EmailVerificationBannerProps) {
  const { status, message, resend } = useResendVerification();

  if (!currentUser || isEmailVerified(currentUser)) {
    return null;
  }

  return (
    <section
      aria-labelledby="email-verification-title"
      className="rounded-lg border border-warning/30 bg-warning-muted p-4 text-sm text-foreground sm:p-5"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="font-semibold" id="email-verification-title">Tu correo aún no está verificado.</h2>
          <p className="mt-2 leading-6 text-muted-foreground">
            Verifica tu correo para activar identificadores, editar tu perfil de emergencia y publicarlo.
          </p>
        </div>
        <Button
          className="w-full sm:w-auto"
          disabled={status === "sending"}
          onClick={() => void resend()}
          type="button"
          variant="outline"
        >
          {status === "sending" ? "Enviando..." : "Reenviar correo de verificación"}
        </Button>
      </div>
      {message ? (
        <p
          className={`mt-4 rounded-md border px-3 py-2 font-medium ${
            status === "error" ? "border-danger/30 bg-danger-muted text-danger" : "border-success/30 bg-success-muted text-success"
          }`}
        >
          {message}
        </p>
      ) : null}
    </section>
  );
}
