import { StatusBadge } from "@/components/ui/status-badge";
import { getBlockingReasonLabel } from "@/components/dashboard/protegid/types";
import type { PublicAccessStatusState } from "@/components/dashboard/protegid/use-protegid-devices";

export interface PublicAccessStatusRowProps {
  state: PublicAccessStatusState | undefined;
}

export function PublicAccessStatusRow({ state }: PublicAccessStatusRowProps) {
  const isLoading = !state || state.isLoading;
  const hasError = state?.hasError ?? false;
  const isOperational = state?.status?.is_operational ?? false;

  const label = isLoading ? "Consultando..." : hasError ? "Estado no disponible" : isOperational ? "Disponible" : "No disponible";
  const variant = isLoading ? "neutral" : hasError ? "neutral" : isOperational ? "success" : "warning";

  return (
    <div className="rounded-lg border border-border bg-surface-muted p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h4 className="text-sm font-semibold text-foreground">Acceso a la ficha</h4>
        <StatusBadge label={label} variant={variant} />
      </div>

      {hasError ? (
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          No se pudo consultar el acceso público de este ProtegID.
        </p>
      ) : null}

      {!isLoading && !hasError && state?.status && state.status.blocking_reasons.length > 0 ? (
        <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
          {state.status.blocking_reasons.map((reason) => (
            <li key={reason}>{getBlockingReasonLabel(reason)}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
