import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  getProfilePublicationStateLabel,
  getProfilePublicationStateVariant,
  getReadinessFieldLabel,
} from "@/components/dashboard/profile/types";
import type { EmergencyProfile, EmergencyProfileStatus } from "@/types/emergency-profile";

export interface ProfileStatusCardProps {
  profile: EmergencyProfile | null;
  profileStatus: EmergencyProfileStatus | null;
  isLoading: boolean;
}

export function ProfileStatusCard({ profile, profileStatus, isLoading }: ProfileStatusCardProps) {
  const requiredCount = profileStatus?.readiness.required_fields.length ?? 0;
  const completedCount = profileStatus
    ? profileStatus.readiness.required_fields.length - profileStatus.readiness.missing_fields.length
    : 0;
  const missingCount = profileStatus?.readiness.missing_fields.length ?? 0;

  return (
    <Card aria-labelledby="profile-status-title">
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Preparación del perfil</p>
          <CardTitle className="mt-1" id="profile-status-title">
            Estado del perfil
          </CardTitle>
        </div>
        <StatusBadge
          label={isLoading ? "Consultando..." : getProfilePublicationStateLabel(profile, profileStatus)}
          variant={isLoading ? "neutral" : getProfilePublicationStateVariant(profile, profileStatus)}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {!profileStatus ? (
          <p className="text-sm text-muted-foreground">
            {isLoading ? "Consultando estado del perfil..." : "No se pudo consultar el estado del perfil."}
          </p>
        ) : (
          <>
            <div>
              <div className="flex items-center justify-between gap-3 text-sm font-medium text-foreground">
                <span>Campos obligatorios</span>
                <span>
                  {completedCount}/{requiredCount}
                </span>
              </div>
              <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-surface-muted ring-1 ring-border">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${requiredCount > 0 ? (completedCount / requiredCount) * 100 : 0}%` }}
                />
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {missingCount > 0
                  ? `Completa ${missingCount} dato${missingCount === 1 ? "" : "s"} para dejar tu perfil listo.`
                  : "Todos los campos obligatorios están completos."}
              </p>
            </div>

            {profileStatus.publication_eligibility.can_publish && profile?.is_public ? (
              <p className="rounded-lg border border-success/30 bg-success-muted px-4 py-3 text-sm font-medium text-success">
                Tu perfil está público: tus identificadores activos pueden mostrar tu ficha de emergencia.
              </p>
            ) : null}

            {profileStatus.readiness.is_ready && profileStatus.publication_eligibility.consent_valid && !profile?.is_public ? (
              <p className="rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 text-sm font-medium text-primary">
                Tu perfil está listo para publicar.
              </p>
            ) : null}

            {missingCount > 0 ? (
              <div className="rounded-lg border border-warning/30 bg-warning-muted p-4">
                <h3 className="text-sm font-semibold text-foreground">Campos faltantes</h3>
                <ul className="mt-2 space-y-1.5 text-sm text-foreground">
                  {profileStatus.readiness.missing_fields.map((field) => (
                    <li key={field}>{getReadinessFieldLabel(field)}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {profileStatus.readiness.is_ready && !profileStatus.publication_eligibility.consent_valid ? (
              <div className="rounded-lg border border-border bg-surface-muted p-4">
                <h3 className="text-sm font-semibold text-foreground">Pendiente</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  Falta aceptar el consentimiento de publicación vigente (versión{" "}
                  {profileStatus.publication_eligibility.consent_version}).
                </p>
              </div>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
