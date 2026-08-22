type NullableString = string | null;

/**
 * Perfil de emergencia — account-scoped (ProtectedPerson), no Device.
 * El backend puede incluir un campo device_id legacy en el payload; el
 * frontend lo ignora deliberadamente y no lo modela aquí.
 */
export type EmergencyProfile = {
  id: string;
  display_name: NullableString;
  blood_type: NullableString;
  allergies: NullableString;
  medical_conditions: NullableString;
  medications: NullableString;
  emergency_contact_name: NullableString;
  emergency_contact_phone: NullableString;
  emergency_contact_relationship: NullableString;
  notes: NullableString;
  is_public: boolean;
  medical_conditions_none: boolean;
  allergies_none: boolean;
  medications_none: boolean;
  public_consent_accepted_at: string | null;
  public_consent_version: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type EmergencyProfileInput = {
  display_name?: NullableString;
  blood_type?: NullableString;
  allergies?: NullableString;
  medical_conditions?: NullableString;
  medications?: NullableString;
  emergency_contact_name?: NullableString;
  emergency_contact_phone?: NullableString;
  emergency_contact_relationship?: NullableString;
  notes?: NullableString;
  is_public?: boolean;
  medical_conditions_none?: boolean;
  allergies_none?: boolean;
  medications_none?: boolean;
  public_consent_accepted_at?: string | null;
  public_consent_version?: string | null;
};

/** Depende exclusivamente del EmergencyProfile. Nunca depende de un Device. */
export type ProfileReadiness = {
  is_ready: boolean;
  required_fields: string[];
  completed_fields: string[];
  missing_fields: string[];
};

/** Perfil + consentimiento. Sigue sin depender de Device. */
export type PublicationEligibility = {
  profile_ready: boolean;
  consent_valid: boolean;
  can_publish: boolean;
  consent_version: string;
};

/** GET /api/emergency-profile/status. No requiere que el perfil exista. */
export type EmergencyProfileStatus = {
  readiness: ProfileReadiness;
  publication_eligibility: PublicationEligibility;
};

/**
 * Unico nivel que combina Device + ProtectedPerson + EmergencyProfile.
 * Especifico de un device/public_id concreto: "¿este identificador puede
 * exponer el perfil ahora?". No es ProfileReadiness.
 */
export type PublicAccessStatus = {
  is_operational: boolean;
  device_status: string | null;
  blocking_reasons: string[];
};
