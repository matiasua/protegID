"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export interface ActivationCardProps {
  emailVerified: boolean;
  isActivating: boolean;
  errorMessage: string | null;
  successMessage: string | null;
  onActivate: (publicId: string, claimCode: string) => Promise<boolean>;
  onDismissMessages: () => void;
}

export function ActivationCard({
  emailVerified,
  isActivating,
  errorMessage,
  successMessage,
  onActivate,
  onDismissMessages,
}: ActivationCardProps) {
  const [publicId, setPublicId] = useState("");
  const [claimCode, setClaimCode] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedPublicId = publicId.trim();
    const trimmedClaimCode = claimCode.trim();

    onDismissMessages();
    setClaimCode("");

    const activated = await onActivate(trimmedPublicId, trimmedClaimCode);

    if (activated) {
      setPublicId("");
    }
  }

  const disabled = isActivating || !emailVerified;

  return (
    <Card aria-labelledby="activation-title">
      <CardHeader>
        <CardDescription className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
          Vinculación
        </CardDescription>
        <CardTitle id="activation-title">Activar identificador</CardTitle>
        <CardDescription>
          Ingresa el Public ID del identificador y el código de activación incluidos con el producto físico.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!emailVerified ? (
          <p className="rounded-lg border border-warning/30 bg-warning-muted px-4 py-3 text-sm font-medium text-warning">
            Debes verificar tu correo antes de activar este identificador.
          </p>
        ) : null}

        <form className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end" onSubmit={(event) => void handleSubmit(event)}>
          <div>
            <label className="text-sm font-medium text-foreground" htmlFor="activation-public-id">
              Public ID
            </label>
            <input
              autoComplete="off"
              className="mt-2 w-full rounded-md border border-input bg-background px-4 py-3 font-mono text-sm uppercase text-foreground shadow-sm outline-none transition placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring"
              disabled={disabled}
              id="activation-public-id"
              onChange={(event) => setPublicId(event.target.value)}
              placeholder="PID-XXXXXXXXXX"
              type="text"
              value={publicId}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground" htmlFor="activation-claim-code">
              Código de activación
            </label>
            <input
              autoComplete="off"
              className="mt-2 w-full rounded-md border border-input bg-background px-4 py-3 font-mono text-sm uppercase text-foreground shadow-sm outline-none transition placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring"
              disabled={disabled}
              id="activation-claim-code"
              onChange={(event) => setClaimCode(event.target.value)}
              placeholder="XXXX-XXXX-XXXX"
              type="password"
              value={claimCode}
            />
          </div>
          <Button
            className="w-full md:w-auto"
            disabled={disabled || publicId.trim().length === 0 || claimCode.trim().length === 0}
            type="submit"
          >
            {isActivating ? "Activando..." : "Activar identificador"}
          </Button>
        </form>

        <p className="text-xs leading-5 text-muted-foreground">
          El código de activación no se guarda en el navegador y no se vuelve a mostrar después de activar.
        </p>

        {successMessage ? (
          <p className="rounded-lg border border-success/30 bg-success-muted px-4 py-3 text-sm font-medium text-success" role="status">
            {successMessage}
          </p>
        ) : null}

        {errorMessage ? (
          <p className="rounded-lg border border-danger/30 bg-danger-muted px-4 py-3 text-sm font-medium text-danger" role="alert">
            {errorMessage}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
