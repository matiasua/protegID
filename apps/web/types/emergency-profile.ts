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
};
