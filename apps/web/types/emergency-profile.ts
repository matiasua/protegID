type NullableString = string | null;

export type EmergencyProfile = {
  id: string;
  device_id: string;
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

export type EmergencyProfileReadiness = {
  is_ready: boolean;
  can_publish: boolean;
  is_public_operational: boolean;
  device_status: string | null;
  public_profile_enabled: boolean;
  required_fields: string[];
  completed_fields: string[];
  missing_fields: string[];
  blocking_reasons: string[];
  consent_version: string;
};
