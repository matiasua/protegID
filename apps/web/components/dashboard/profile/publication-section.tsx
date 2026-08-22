import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckboxField } from "@/components/dashboard/profile/form-controls";
import { isConsentAccepted, type ProfileFormState } from "@/components/dashboard/profile/types";
import type { EmergencyProfileStatus } from "@/types/emergency-profile";

export interface PublicationSectionProps {
  form: ProfileFormState;
  profileStatus: EmergencyProfileStatus | null;
  disabled: boolean;
  onChangeConsent: (checked: boolean) => void;
  onChangeIsPublic: (checked: boolean) => void;
}

function getPublishBlockedReason(profileStatus: EmergencyProfileStatus | null): string | null {
  if (!profileStatus) {
    return null;
  }

  if (!profileStatus.readiness.is_ready) {
    return "Completa los campos obligatorios para poder publicar.";
  }

  if (!profileStatus.publication_eligibility.consent_valid) {
    return "Guarda el consentimiento de publicación para habilitar la publicación.";
  }

  if (!profileStatus.publication_eligibility.can_publish) {
    return "El perfil aún no está listo para publicarse.";
  }

  return null;
}

export function PublicationSection({
  form,
  profileStatus,
  disabled,
  onChangeConsent,
  onChangeIsPublic,
}: PublicationSectionProps) {
  const consentAccepted = isConsentAccepted(form, profileStatus);

  // Apagar publicación siempre está permitido. Habilitarla depende
  // exclusivamente de publication_eligibility.can_publish persistido por el
  // backend (nunca se recalcula en el frontend).
  const canEnablePublic = profileStatus?.publication_eligibility.can_publish ?? false;
  const isPublicToggleDisabled = disabled || (!form.is_public && !canEnablePublic);
  const publishBlockedReason = !form.is_public ? getPublishBlockedReason(profileStatus) : null;

  return (
    <Card aria-labelledby="publication-title">
      <CardHeader>
        <CardTitle id="publication-title">Consentimiento y publicación</CardTitle>
        <p className="text-sm leading-6 text-muted-foreground">
          El consentimiento de publicación y la visibilidad pública son decisiones independientes.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <CheckboxField
          checked={consentAccepted}
          disabled={disabled || !profileStatus}
          helpText={
            profileStatus
              ? `Versión de consentimiento: ${profileStatus.publication_eligibility.consent_version}`
              : undefined
          }
          id="profile-consent"
          label={
            <>
              <span className="block font-semibold text-foreground">
                Acepto la publicación de mi ficha de emergencia
              </span>
              <span className="mt-1 block text-muted-foreground">
                Acepto que ProtegID muestre públicamente mi información de emergencia al escanear el QR/NFC de
                cualquiera de mis identificadores físicos activos.
              </span>
            </>
          }
          onChange={onChangeConsent}
        />

        <CheckboxField
          checked={form.is_public}
          disabled={isPublicToggleDisabled}
          helpText={publishBlockedReason ?? undefined}
          id="profile-is-public"
          label={
            <>
              <span className="block font-semibold text-foreground">Habilitar perfil público</span>
              <span className="mt-1 block text-muted-foreground">
                Controla si tu perfil se muestra en tus identificadores ProtegID activos. El backend solo lo
                publicará si cumple los mínimos y el consentimiento vigente.
              </span>
            </>
          }
          onChange={onChangeIsPublic}
        />
      </CardContent>
    </Card>
  );
}
