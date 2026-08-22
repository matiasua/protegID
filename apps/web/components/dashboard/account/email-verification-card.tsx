"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { isEmailVerified } from "@/components/dashboard/account/types";
import { useResendVerification } from "@/components/dashboard/account/use-resend-verification";
import type { AuthUser } from "@/types/auth";

export interface EmailVerificationCardProps {
  user: AuthUser;
}

export function EmailVerificationCard({ user }: EmailVerificationCardProps) {
  const verified = isEmailVerified(user);
  const { status, message, resend } = useResendVerification();

  return (
    <Card aria-labelledby="email-verification-account-title" surface={verified ? "default" : "warning"}>
      <CardHeader className="space-y-0">
        <CardTitle id="email-verification-account-title">Correo electrónico</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {verified ? (
          <StatusBadge label="Correo verificado" variant="success" />
        ) : (
          <>
            <StatusBadge label="Correo no verificado" variant="warning" />
            <p className="text-sm leading-6 text-muted-foreground">
              Tu correo aún no está verificado. Reenvía el enlace de verificación a {user.email}.
            </p>
            <Button
              className="w-full sm:w-auto"
              disabled={status === "sending"}
              onClick={() => void resend()}
              type="button"
              variant="outline"
            >
              {status === "sending" ? "Enviando..." : "Reenviar correo de verificación"}
            </Button>
            {message ? (
              <p
                className={`rounded-md border px-3 py-2 text-sm font-medium ${
                  status === "error"
                    ? "border-danger/30 bg-danger-muted text-danger"
                    : "border-success/30 bg-success-muted text-success"
                }`}
                role={status === "error" ? "alert" : "status"}
              >
                {message}
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
