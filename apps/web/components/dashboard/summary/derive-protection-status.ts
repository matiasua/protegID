import type { Device } from "@/types/device";
import type { EmergencyProfile, EmergencyProfileStatus } from "@/types/emergency-profile";
import type { PublicAccessStatusState } from "@/components/dashboard/summary/use-dashboard-summary";

/**
 * Todo lo de este archivo es UI DERIVATION (composición de presentación),
 * no una nueva fuente de verdad persistida. El dominio real sigue viviendo en
 * ProfileReadiness, PublicationEligibility, EmergencyProfile.is_public y
 * PublicAccessStatus. Este helper solo decide copy/variant/CTA a partir de
 * esos estados ya existentes.
 */

export type DeviceAggregation = {
  total: number;
  operationalCount: number;
  attentionCount: number;
  pendingCount: number;
  isSettled: boolean;
};

export function aggregateDevicePublicAccess(
  devices: Device[],
  publicAccessByDeviceId: Record<string, PublicAccessStatusState>,
): DeviceAggregation {
  let operationalCount = 0;
  let attentionCount = 0;
  let pendingCount = 0;

  for (const device of devices) {
    const state = publicAccessByDeviceId[device.id];

    if (!state || state.isLoading) {
      pendingCount += 1;
      continue;
    }

    if (state.hasError) {
      // Estado no determinado (fallo puntual de consulta): se trata como
      // "requiere atención" para no afirmar que el ProtegID está operativo,
      // sin declararlo defectuoso.
      attentionCount += 1;
      continue;
    }

    if (state.status?.is_operational) {
      operationalCount += 1;
    } else {
      attentionCount += 1;
    }
  }

  return {
    total: devices.length,
    operationalCount,
    attentionCount,
    pendingCount,
    isSettled: pendingCount === 0,
  };
}

export type ProtectionStatusVariant = "neutral" | "info" | "success" | "warning" | "danger";

export type ProtectionStatusScenario =
  | "unknown"
  | "profile-unknown"
  | "no-profile"
  | "incomplete"
  | "consent-pending"
  | "eligible-private"
  | "public-devices-unknown"
  | "public-no-devices"
  | "public-devices-pending"
  | "public-no-operational"
  | "public-mixed"
  | "public-all-operational";

export type ProtectionStatusCta = {
  label: string;
  href: string;
};

export type ProtectionStatusPresentation = {
  scenario: ProtectionStatusScenario;
  variant: ProtectionStatusVariant;
  headline: string;
  description: string | null;
  primaryCta: ProtectionStatusCta | null;
  secondaryCta: ProtectionStatusCta | null;
};

export function deriveProtectionStatus(
  profile: EmergencyProfile | null,
  profileStatus: EmergencyProfileStatus | null,
  deviceAggregation: DeviceAggregation,
  profileErrorMessage: string | null,
  devicesErrorMessage: string | null,
): ProtectionStatusPresentation {
  // A0. Falla de consulta del perfil (network/5xx): profile===null aquí no
  // es un 404 válido, es "desconocido". No debe leerse como "sin ficha".
  if (profileErrorMessage) {
    return {
      scenario: "profile-unknown",
      variant: "neutral",
      headline: "No pudimos comprobar el estado de tu ficha de emergencia.",
      description: "Intenta nuevamente en unos momentos.",
      primaryCta: null,
      secondaryCta: null,
    };
  }

  // A. Sin perfil (404 válido).
  if (profile === null) {
    return {
      scenario: "no-profile",
      variant: "neutral",
      headline: "Aún no tienes tu ficha de emergencia.",
      description: "Crea tu perfil de emergencia para poder publicarlo en un ProtegID.",
      primaryCta: { label: "Crear perfil", href: "/dashboard/perfil" },
      secondaryCta: { label: "Activar ProtegID", href: "/dashboard/protegid" },
    };
  }

  if (!profileStatus) {
    return {
      scenario: "unknown",
      variant: "neutral",
      headline: "No pudimos consultar el estado de tu perfil.",
      description: "Intenta nuevamente en unos momentos.",
      primaryCta: null,
      secondaryCta: null,
    };
  }

  // B. Perfil incompleto.
  if (!profileStatus.readiness.is_ready) {
    const missingCount = profileStatus.readiness.missing_fields.length;

    return {
      scenario: "incomplete",
      variant: "warning",
      headline:
        missingCount > 0
          ? `Completa ${missingCount} dato${missingCount === 1 ? "" : "s"} para dejar tu perfil listo.`
          : "Tu perfil de emergencia está incompleto.",
      description: "Un ProtegID activo no cambia este requisito: tu perfil debe estar completo antes de publicarse.",
      primaryCta: { label: "Completar perfil", href: "/dashboard/perfil" },
      secondaryCta: null,
    };
  }

  // C. Ready + consentimiento no válido.
  if (!profileStatus.publication_eligibility.consent_valid) {
    return {
      scenario: "consent-pending",
      variant: "warning",
      headline: "Tu perfil está completo. Revisa el consentimiento para poder publicarlo.",
      description: "Necesitas aceptar el consentimiento de publicación vigente antes de hacer público tu perfil.",
      primaryCta: { label: "Revisar consentimiento", href: "/dashboard/perfil" },
      secondaryCta: null,
    };
  }

  // D. Ready + eligible + privado.
  if (!profile.is_public) {
    return {
      scenario: "eligible-private",
      variant: "info",
      headline: "Tu perfil está listo para publicar.",
      description: "Publica tu perfil para que tus ProtegID activos puedan mostrarlo.",
      primaryCta: { label: "Publicar perfil", href: "/dashboard/perfil" },
      secondaryCta: null,
    };
  }

  // E. Público + cero Devices.
  if (deviceAggregation.total === 0) {
    // total===0 puede ser una lista realmente vacía o una consulta fallida
    // (GET /api/devices con error): no son el mismo estado.
    if (devicesErrorMessage) {
      return {
        scenario: "public-devices-unknown",
        variant: "neutral",
        headline: "No pudimos comprobar el estado de tus ProtegID.",
        description: "Intenta nuevamente en unos momentos.",
        primaryCta: null,
        secondaryCta: null,
      };
    }

    return {
      scenario: "public-no-devices",
      variant: "info",
      headline: "Tu perfil está público, pero aún no tienes un ProtegID asociado.",
      description: "Activa un identificador ProtegID para que tu ficha de emergencia pueda mostrarse.",
      primaryCta: { label: "Activar ProtegID", href: "/dashboard/protegid" },
      secondaryCta: null,
    };
  }

  if (!deviceAggregation.isSettled) {
    return {
      scenario: "public-devices-pending",
      variant: "neutral",
      headline: "Consultando el estado de tus ProtegID...",
      description: null,
      primaryCta: null,
      secondaryCta: null,
    };
  }

  // F. Público + cero Devices operativos.
  if (deviceAggregation.operationalCount === 0) {
    return {
      scenario: "public-no-operational",
      variant: "warning",
      headline: "Tu perfil está listo, pero ninguno de tus ProtegID puede mostrarlo actualmente.",
      description: "Revisa el estado de tus identificadores para restablecer el acceso.",
      primaryCta: { label: "Revisar ProtegID", href: "/dashboard/protegid" },
      secondaryCta: null,
    };
  }

  // G. Público + >=1 operativo + algún problema.
  if (deviceAggregation.attentionCount > 0) {
    const headline =
      deviceAggregation.attentionCount === 1
        ? "Tu perfil está público y disponible. 1 ProtegID requiere atención."
        : `Tu perfil está público y disponible. ${deviceAggregation.attentionCount} ProtegID requieren atención.`;

    return {
      scenario: "public-mixed",
      variant: "success",
      headline,
      description: "Al menos uno de tus ProtegID está mostrando tu ficha de emergencia correctamente.",
      primaryCta: null,
      secondaryCta: { label: "Gestionar ProtegID", href: "/dashboard/protegid" },
    };
  }

  // H. Público + todos operativos.
  return {
    scenario: "public-all-operational",
    variant: "success",
    headline: "Tu perfil está público y tus ProtegID están operativos.",
    description: "Todos tus identificadores activos pueden mostrar tu ficha de emergencia.",
    primaryCta: null,
    secondaryCta: { label: "Gestionar perfil", href: "/dashboard/perfil" },
  };
}
