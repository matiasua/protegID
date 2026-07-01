"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { ApiRequestError } from "@/lib/api";
import { getCurrentUser, resendVerification } from "@/lib/auth";
import { activateDeviceWithClaimCode } from "@/lib/devices";
import type { AuthUser } from "@/types/auth";

type ActivationFormProps = {
  publicId: string;
};

type ResendVerificationStatus = "idle" | "sending" | "sent" | "error";

const EMAIL_VERIFICATION_REQUIRED_MESSAGE = "Debes verificar tu correo antes de realizar esta acción.";

function isEmailVerified(user: AuthUser | null): boolean {
  return user?.email_verified_at !== null && user?.email_verified_at !== undefined;
}

function getResendVerificationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }

  return "No se pudo reenviar el correo de verificación.";
}

export function ActivationForm({ publicId }: ActivationFormProps) {
  const activationPath = `/p/${publicId}`;
  const loginHref = `/login?returnTo=${activationPath}`;
  const registerHref = `/register?returnTo=${activationPath}`;
  const dashboardHref = `/dashboard?publicId=${encodeURIComponent(publicId)}`;
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [claimCode, setClaimCode] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [resendVerificationStatus, setResendVerificationStatus] = useState<ResendVerificationStatus>("idle");
  const [resendVerificationMessage, setResendVerificationMessage] = useState<string | null>(null);
  const [isActivating, setIsActivating] = useState(false);
  const hasSession = currentUser !== null;
  const emailVerified = isEmailVerified(currentUser);

  useEffect(() => {
    getCurrentUser()
      .then((user) => setCurrentUser(user))
      .catch(() => setCurrentUser(null))
      .finally(() => setSessionChecked(true));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!hasSession || isActivating) {
      return;
    }

    const submittedClaimCode = claimCode.trim();
    setClaimCode("");
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!emailVerified) {
      setErrorMessage(EMAIL_VERIFICATION_REQUIRED_MESSAGE);
      return;
    }

    if (submittedClaimCode.length === 0) {
      setErrorMessage("Código de activación inválido o incompleto.");
      return;
    }

    setIsActivating(true);

    try {
      await activateDeviceWithClaimCode(publicId, submittedClaimCode);
      setSuccessMessage("Identificador vinculado correctamente.");
    } catch (error) {
      if (error instanceof ApiRequestError) {
        if (error.status === 401) {
          setCurrentUser(null);
        }
        setErrorMessage(error.status === 403 ? EMAIL_VERIFICATION_REQUIRED_MESSAGE : error.message);
      } else {
        setErrorMessage("No se pudo activar el identificador.");
      }
    } finally {
      setIsActivating(false);
    }
  }

  async function handleResendVerification() {
    setResendVerificationStatus("sending");
    setResendVerificationMessage(null);

    try {
      const response = await resendVerification();
      setResendVerificationStatus("sent");
      setResendVerificationMessage(
        response.verification_sent
          ? "Correo de verificación reenviado. Revisa tu bandeja de entrada."
          : "Tu correo ya figura como verificado.",
      );
    } catch (error) {
      setResendVerificationStatus("error");
      setResendVerificationMessage(getResendVerificationErrorMessage(error));
    }
  }

  if (!sessionChecked) {
    return <p className="text-sm text-slate-500">Verificando sesión...</p>;
  }

  if (!hasSession) {
    return (
      <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div>
          <p className="font-semibold text-slate-950">Inicia sesión para activar este identificador.</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Después de iniciar sesión o crear una cuenta, vuelve a esta URL para ingresar el código de activación
            incluido dentro del empaque.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Link
            className="inline-flex items-center justify-center rounded-full bg-red-700 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2"
            href={loginHref}
          >
            Iniciar sesión
          </Link>
          <Link
            className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-800 shadow-sm transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
            href={registerHref}
          >
            Crear cuenta
          </Link>
        </div>
      </div>
    );
  }

  if (successMessage) {
    return (
      <div className="space-y-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <p className="font-semibold text-emerald-950">{successMessage}</p>
        <p className="text-sm leading-6 text-emerald-900">
          Ahora completa tu perfil de emergencia para que el QR/NFC pueda mostrar información útil cuando sea necesario.
        </p>
        <Link
          className="inline-flex items-center justify-center rounded-full bg-emerald-700 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
          href={dashboardHref}
        >
          Completar perfil de emergencia
        </Link>
      </div>
    );
  }

  if (!emailVerified) {
    return (
      <div className="space-y-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <div>
          <p className="font-semibold text-amber-950">Debes verificar tu correo antes de activar este identificador.</p>
          <p className="mt-1 text-sm leading-6 text-amber-900">
            Revisa tu email o reenvía el correo de verificación desde esta sesión.
          </p>
        </div>

        <button
          className="inline-flex w-full items-center justify-center rounded-full border border-amber-300 bg-white px-5 py-3 text-sm font-bold text-amber-950 shadow-sm transition hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto"
          disabled={resendVerificationStatus === "sending"}
          onClick={() => void handleResendVerification()}
          type="button"
        >
          {resendVerificationStatus === "sending" ? "Enviando..." : "Reenviar correo de verificación"}
        </button>

        {resendVerificationMessage ? (
          <p className={`rounded-xl border px-3 py-2 text-sm font-semibold ${resendVerificationStatus === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-emerald-200 bg-white text-emerald-800"}`}>
            {resendVerificationMessage}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <form className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4" onSubmit={handleSubmit}>
      <div>
        <label className="text-sm font-bold text-slate-950" htmlFor="claim-code">
          Código de activación
        </label>
        <input
          autoComplete="off"
          className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 font-mono text-base text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-red-700 focus:ring-2 focus:ring-red-100"
          disabled={isActivating}
          id="claim-code"
          inputMode="text"
          onChange={(event) => setClaimCode(event.target.value)}
          placeholder="XXXX-XXXX-XXXX"
          type="text"
          value={claimCode}
        />
      </div>

      {errorMessage ? <p className="text-sm font-semibold text-red-700">{errorMessage}</p> : null}

      <button
        className="inline-flex w-full items-center justify-center rounded-full bg-red-700 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400 sm:w-auto"
        disabled={isActivating}
        type="submit"
      >
        {isActivating ? "Activando..." : "Activar identificador"}
      </button>
    </form>
  );
}
