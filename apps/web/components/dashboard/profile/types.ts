import { ApiRequestError } from "@/lib/api";
import type {
  EmergencyProfile,
  EmergencyProfileInput,
  EmergencyProfileStatus,
} from "@/types/emergency-profile";

export const EMAIL_VERIFICATION_REQUIRED_MESSAGE = "Debes verificar tu correo antes de realizar esta acción.";

export type ProfileFormState = {
  display_name: string;
  blood_type: string;
  allergies: string;
  medical_conditions: string;
  medications: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relationship: string;
  notes: string;
  is_public: boolean;
  medical_conditions_none: boolean;
  allergies_none: boolean;
  medications_none: boolean;
  public_consent_accepted_at: string | null;
  public_consent_version: string | null;
};

export type ProfileTextFieldName =
  | "display_name"
  | "blood_type"
  | "allergies"
  | "medical_conditions"
  | "medications"
  | "emergency_contact_name"
  | "emergency_contact_phone"
  | "emergency_contact_relationship"
  | "notes";

export type ProfileDecisionFieldName = "medical_conditions_none" | "allergies_none" | "medications_none";

export function createEmptyProfileForm(): ProfileFormState {
  return {
    display_name: "",
    blood_type: "",
    allergies: "",
    medical_conditions: "",
    medications: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relationship: "",
    notes: "",
    is_public: false,
    medical_conditions_none: false,
    allergies_none: false,
    medications_none: false,
    public_consent_accepted_at: null,
    public_consent_version: null,
  };
}

export function createProfileForm(profile: EmergencyProfile): ProfileFormState {
  return {
    display_name: profile.display_name ?? "",
    blood_type: profile.blood_type ?? "",
    allergies: profile.allergies ?? "",
    medical_conditions: profile.medical_conditions ?? "",
    medications: profile.medications ?? "",
    emergency_contact_name: profile.emergency_contact_name ?? "",
    emergency_contact_phone: profile.emergency_contact_phone ?? "",
    emergency_contact_relationship: profile.emergency_contact_relationship ?? "",
    notes: profile.notes ?? "",
    is_public: profile.is_public,
    medical_conditions_none: profile.medical_conditions_none,
    allergies_none: profile.allergies_none,
    medications_none: profile.medications_none,
    public_consent_accepted_at: profile.public_consent_accepted_at,
    public_consent_version: profile.public_consent_version,
  };
}

function normalizeProfileValue(value: string): string | null {
  const normalizedValue = value.trim();
  return normalizedValue.length > 0 ? normalizedValue : null;
}

export function createProfilePayload(form: ProfileFormState): EmergencyProfileInput {
  return {
    display_name: normalizeProfileValue(form.display_name),
    blood_type: normalizeProfileValue(form.blood_type),
    allergies: form.allergies_none ? null : normalizeProfileValue(form.allergies),
    medical_conditions: form.medical_conditions_none ? null : normalizeProfileValue(form.medical_conditions),
    medications: form.medications_none ? null : normalizeProfileValue(form.medications),
    emergency_contact_name: normalizeProfileValue(form.emergency_contact_name),
    emergency_contact_phone: normalizeProfileValue(form.emergency_contact_phone),
    emergency_contact_relationship: normalizeProfileValue(form.emergency_contact_relationship),
    notes: normalizeProfileValue(form.notes),
    is_public: form.is_public,
    medical_conditions_none: form.medical_conditions_none,
    allergies_none: form.allergies_none,
    medications_none: form.medications_none,
    public_consent_accepted_at: form.public_consent_accepted_at,
    public_consent_version: form.public_consent_version,
  };
}

export function isConsentAccepted(form: ProfileFormState, profileStatus: EmergencyProfileStatus | null): boolean {
  return Boolean(
    form.public_consent_accepted_at &&
      form.public_consent_version &&
      (!profileStatus || form.public_consent_version === profileStatus.publication_eligibility.consent_version),
  );
}

export function getReadinessFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    display_name: "Nombre visible",
    emergency_contact_name: "Nombre del contacto de emergencia",
    emergency_contact_phone: "Teléfono del contacto de emergencia",
    medical_conditions_decision: "Declarar condiciones médicas o marcar que no hay",
    allergies_decision: "Declarar alergias o marcar que no hay",
  };

  return labels[field] ?? field;
}

/**
 * Estado de publicación del perfil (cuenta), independiente de cualquier
 * Device: A) incompleto, B) listo pero sin consentimiento vigente,
 * C) elegible pero privado, D) público.
 */
export function getProfilePublicationStateLabel(
  profile: EmergencyProfile | null,
  profileStatus: EmergencyProfileStatus | null,
): string {
  if (!profileStatus) {
    return "Consultando perfil";
  }

  if (!profileStatus.readiness.is_ready) {
    return "Perfil incompleto";
  }

  if (!profileStatus.publication_eligibility.consent_valid) {
    return "Perfil listo, falta consentimiento vigente";
  }

  if (!profile?.is_public) {
    return "Perfil listo para publicar";
  }

  return "Perfil público";
}

export type ProfilePublicationVariant = "neutral" | "warning" | "info" | "success";

export function getProfilePublicationStateVariant(
  profile: EmergencyProfile | null,
  profileStatus: EmergencyProfileStatus | null,
): ProfilePublicationVariant {
  if (!profileStatus) {
    return "neutral";
  }

  if (!profileStatus.readiness.is_ready || !profileStatus.publication_eligibility.consent_valid) {
    return "warning";
  }

  if (profile?.is_public) {
    return "success";
  }

  return "info";
}

export function getProfileErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiRequestError && error.status === 401) {
    return "No autorizado para gestionar este perfil de emergencia.";
  }

  if (error instanceof ApiRequestError && error.status === 403) {
    return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
  }

  if (error instanceof ApiRequestError && error.status === 409) {
    return "Error de integridad del perfil de emergencia. Contacta a soporte.";
  }

  if (error instanceof ApiRequestError && error.status === 422) {
    return "Completa los campos obligatorios antes de publicar el perfil.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallbackMessage;
}
