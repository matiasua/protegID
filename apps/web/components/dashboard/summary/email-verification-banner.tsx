"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { resendVerification } from "@/lib/auth";
import type { AuthUser } from "@/types/auth";

type ResendVerificationStatus = "idle" | "sending" | "sent" | "error";

function isEmailVerified(user: AuthUser | null): boolean {
  return user?.email_verified_at !== null && user?.email_verified_at !== undefined;
}

function getResendVerificationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }

  return "No se pudo reenviar el correo de verificación.";
}

export interface EmailVerificationBannerProps {
  currentUser: AuthUser | null;
}

export function EmailVerificationBanner({ currentUser }: EmailVerificationBannerProps) {
  const [status, setStatus] = useState<ResendVerificationStatus>("idle");
  const [message, setMessage] = useState<string | null>(null);

  if (!currentUser || isEmailVerified(currentUser)) {
    return null;
  }

  async function handleResendVerification() {
    setStatus("sending");
    setMessage(null);

    try {
      const response = await resendVerification();
      setStatus("sent");
      setMessage(
        response.verification_sent
          ? "Correo de verificación reenviado. Revisa tu bandeja de entrada."
          : "Tu correo ya figura como verificado.",
      );
    } catch (error) {
      setStatus("error");
      setMessage(getResendVerificationErrorMessage(error));
    }
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
          onClick={() => void handleResendVerification()}
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
