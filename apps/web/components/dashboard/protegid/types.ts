import { ApiRequestError } from "@/lib/api";
import type { StatusBadgeVariant } from "@/components/ui/status-badge";
import type { Device, DeviceStatus } from "@/types/device";

export const EMAIL_VERIFICATION_REQUIRED_MESSAGE = "Debes verificar tu correo antes de realizar esta acción.";

export function isAdminUser(role: string | undefined): boolean {
  return role?.toLowerCase() === "admin";
}

export function getDeviceStatusLabel(status: DeviceStatus): string {
  const labels: Record<DeviceStatus, string> = {
    pending_activation: "Pendiente de activación",
    active: "Activo",
    disabled: "Deshabilitado",
    lost: "Perdido",
  };

  return labels[status];
}

export function getDeviceStatusVariant(status: DeviceStatus): StatusBadgeVariant {
  const variants: Record<DeviceStatus, StatusBadgeVariant> = {
    pending_activation: "neutral",
    active: "success",
    disabled: "warning",
    lost: "danger",
  };

  return variants[status];
}

export function getDeviceStatusDescription(status: DeviceStatus): string {
  const descriptions: Record<DeviceStatus, string> = {
    pending_activation: "Este identificador aún no está vinculado a una cuenta.",
    active: "Este identificador está vinculado a tu cuenta.",
    disabled: "Este identificador está deshabilitado y no debería usarse operacionalmente.",
    lost: "Este identificador fue reportado como perdido. Verifica antes de reutilizarlo.",
  };

  return descriptions[status];
}

export function isDeviceOperational(status: DeviceStatus): boolean {
  return status === "active";
}

const BLOCKING_REASON_LABELS: Record<string, string> = {
  device_missing: "Este ProtegID no está disponible.",
  device_not_active: "Este ProtegID no está activo.",
  device_deleted: "Este ProtegID no está operativo.",
  protected_person_missing: "No hay un perfil de emergencia asociado a esta cuenta.",
  protected_person_deleted: "La cuenta protegida no está disponible.",
  profile_missing: "Aún no existe un perfil de emergencia.",
  profile_deleted: "El perfil de emergencia no está operativo.",
  profile_private: "Tu perfil está privado.",
  publication_not_eligible: "Tu perfil aún no está listo para publicarse.",
};

const FALLBACK_BLOCKING_REASON_LABEL = "Este ProtegID no puede mostrar tu ficha en este momento.";

export function getBlockingReasonLabel(reason: string): string {
  return BLOCKING_REASON_LABELS[reason] ?? FALLBACK_BLOCKING_REASON_LABEL;
}

export function formatActivatedAt(value: string | null): string {
  if (!value) {
    return "No activado";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function getDevicesErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError && (error.status === 401 || error.status === 403)) {
    return "No autorizado para cargar tus identificadores.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No se pudieron cargar tus identificadores.";
}

export function getActivationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 400) {
      return "Datos de activación inválidos.";
    }

    if (error.status === 401) {
      return "Sesión expirada o no autenticada.";
    }

    if (error.status === 403) {
      return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
    }

    if (error.status === 404) {
      return "Identificador no disponible.";
    }

    if (error.status === 422) {
      return "Código de activación inválido o incompleto.";
    }

    if (error.status === 429) {
      return "Demasiados intentos. Intenta nuevamente más tarde.";
    }
  }

  return "No se pudo activar el identificador.";
}

export function getQrGenerationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) {
      return "Sesión expirada o no autenticada.";
    }

    if (error.status === 403) {
      return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
    }

    if (error.status === 404) {
      return "Dispositivo no encontrado.";
    }
  }

  return "No se pudo generar el QR.";
}

export function getQrDownloadErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) {
      return "Sesión expirada o no autenticada.";
    }

    if (error.status === 403) {
      return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
    }

    if (error.status === 404) {
      return "QR no encontrado. Genera el QR antes de descargarlo.";
    }
  }

  return "No se pudo descargar el QR.";
}

export function deviceDisplayName(device: Device): string {
  return device.label?.trim() ? device.label : "Sin etiqueta";
}
