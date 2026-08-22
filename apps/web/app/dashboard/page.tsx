"use client";

import Link from "next/link";
import { Suspense, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboardSession } from "@/app/dashboard/dashboard-session-context";
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

function DashboardContent() {
  const { user: currentUser } = useDashboardSession();
  const [resendVerificationStatus, setResendVerificationStatus] = useState<ResendVerificationStatus>("idle");
  const [resendVerificationMessage, setResendVerificationMessage] = useState<string | null>(null);
  const currentUserEmailVerified = isEmailVerified(currentUser);

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

  return (
    <>
      <PageHeader
        description="Gestiona tu perfil de emergencia y tus identificadores ProtegID. La sesión se mantiene con una cookie HttpOnly emitida por el backend."
        title="Resumen"
      />

      {currentUser && !currentUserEmailVerified ? (
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
              disabled={resendVerificationStatus === "sending"}
              onClick={() => void handleResendVerification()}
              type="button"
              variant="outline"
            >
              {resendVerificationStatus === "sending" ? "Enviando..." : "Reenviar correo de verificación"}
            </Button>
          </div>
          {resendVerificationMessage ? (
            <p className={`mt-4 rounded-md border px-3 py-2 font-medium ${resendVerificationStatus === "error" ? "border-danger/30 bg-danger-muted text-danger" : "border-success/30 bg-success-muted text-success"}`}>
              {resendVerificationMessage}
            </p>
          ) : null}
        </section>
      ) : null}

      {currentUser ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card aria-labelledby="profile-access-title">
            <CardHeader>
              <CardDescription className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                Editor de perfil
              </CardDescription>
              <CardTitle id="profile-access-title">Perfil de emergencia</CardTitle>
              <CardDescription>
                Gestiona los datos médicos y de contacto que se muestran en tus identificadores ProtegID activos.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href="/dashboard/perfil">Gestionar perfil</Link>
              </Button>
            </CardContent>
          </Card>

          <Card aria-labelledby="protegid-access-title">
            <CardHeader>
              <CardDescription className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                Inventario privado
              </CardDescription>
              <CardTitle id="protegid-access-title">Mis ProtegID</CardTitle>
              <CardDescription>
                Activa nuevos identificadores y consulta el estado de tus ProtegID existentes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href="/dashboard/protegid">Gestionar ProtegID</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardContent />
    </Suspense>
  );
}
