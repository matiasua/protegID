"use client";

import { useCallback, useRef, useState } from "react";

import { getResendVerificationErrorMessage } from "@/components/dashboard/account/types";
import { resendVerification } from "@/lib/auth";

export type ResendVerificationStatus = "idle" | "sending" | "sent" | "error";

export type ResendVerificationState = {
  status: ResendVerificationStatus;
  message: string | null;
  resend: () => Promise<void>;
};

/**
 * Fuente única del flujo de reenvío de verificación (usada por el banner del
 * Resumen y por la tarjeta de Cuenta). Evita requests simultáneos mientras
 * uno está en curso.
 */
export function useResendVerification(): ResendVerificationState {
  const [status, setStatus] = useState<ResendVerificationStatus>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const isSendingRef = useRef(false);

  const resend = useCallback(async () => {
    if (isSendingRef.current) {
      return;
    }

    isSendingRef.current = true;
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
    } finally {
      isSendingRef.current = false;
    }
  }, []);

  return { status, message, resend };
}
