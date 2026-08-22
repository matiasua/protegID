import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TextField } from "@/components/dashboard/profile/form-controls";
import type { ProfileFormState, ProfileTextFieldName } from "@/components/dashboard/profile/types";

export interface EmergencyContactSectionProps {
  form: ProfileFormState;
  disabled: boolean;
  onChangeText: (name: ProfileTextFieldName, value: string) => void;
}

export function EmergencyContactSection({ form, disabled, onChangeText }: EmergencyContactSectionProps) {
  return (
    <Card aria-labelledby="emergency-contact-title">
      <CardHeader>
        <CardTitle id="emergency-contact-title">Contacto de emergencia</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <TextField
          disabled={disabled}
          id="profile-emergency-contact-name"
          label="Nombre del contacto"
          onChange={(value) => onChangeText("emergency_contact_name", value)}
          required
          value={form.emergency_contact_name}
        />
        <TextField
          disabled={disabled}
          id="profile-emergency-contact-phone"
          label="Teléfono del contacto"
          onChange={(value) => onChangeText("emergency_contact_phone", value)}
          required
          value={form.emergency_contact_phone}
        />
        <TextField
          className="md:col-span-2"
          disabled={disabled}
          id="profile-emergency-contact-relationship"
          label="Relación con el contacto"
          onChange={(value) => onChangeText("emergency_contact_relationship", value)}
          value={form.emergency_contact_relationship}
        />
      </CardContent>
    </Card>
  );
}
