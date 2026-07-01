"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { verifyEmail } from "@/lib/auth";

type VerificationState = "idle" | "loading" | "success" | "error";

function getVerifyEmailErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 400 || error.status === 422) {
      return "El enlace de verificación no es válido o expiró.";
    }

    if (error.status === 429) {
      return "Demasiados intentos. Intenta más tarde.";
    }
  }

  return "No se pudo verificar el correo. Intenta nuevamente más tarde.";
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token")?.trim() ?? "";
  const hasSubmitted = useRef(false);
  const [state, setState] = useState<VerificationState>("idle");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (hasSubmitted.current) {
      return;
    }

    if (!token) {
      setState("error");
      setMessage("El enlace de verificación no es válido o expiró.");
      return;
    }

    hasSubmitted.current = true;
    setState("loading");
    setMessage(null);

    verifyEmail(token)
      .then(() => {
        setState("success");
        setMessage("Correo verificado correctamente.");
      })
      .catch((error) => {
        setState("error");
        setMessage(getVerifyEmailErrorMessage(error));
      });
  }, [token]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.18),_transparent_30rem)] px-4 py-8 text-slate-950 sm:px-6 lg:py-12">
      <section className="mx-auto flex min-h-[calc(100vh-6rem)] max-w-3xl items-center justify-center">
        <div className="w-full rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <Link className="inline-flex text-sm font-medium text-sky-700 underline-offset-4 hover:underline" href="/">
            Volver al inicio
          </Link>

          <p className="mt-8 text-sm font-semibold uppercase tracking-[0.24em] text-sky-700">Verificación de correo</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Verificar email</h1>

          {state === "loading" ? (
            <p className="mt-6 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm font-medium text-sky-800">
              Verificando correo...
            </p>
          ) : null}

          {state === "success" ? (
            <section className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <p className="font-semibold">{message}</p>
              <p className="mt-2 leading-6">Ya puedes iniciar sesión y continuar con tu dashboard ProtegID.</p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                <Button asChild className="w-full sm:w-auto">
                  <Link href="/login">Iniciar sesión</Link>
                </Button>
                <Button asChild className="w-full sm:w-auto" variant="outline">
                  <Link href="/dashboard">Continuar al dashboard</Link>
                </Button>
              </div>
            </section>
          ) : null}

          {state === "error" ? (
            <section className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <p className="font-semibold">{message}</p>
              <p className="mt-2 leading-6">Inicia sesión para solicitar un nuevo correo de verificación.</p>
              <Button asChild className="mt-4 w-full sm:w-auto">
                <Link href="/login">Iniciar sesión para reenviar verificación</Link>
              </Button>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}
