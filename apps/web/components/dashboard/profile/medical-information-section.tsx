import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TextAreaField, TextField } from "@/components/dashboard/profile/form-controls";
import type {
  ProfileDecisionFieldName,
  ProfileFormState,
  ProfileTextFieldName,
} from "@/components/dashboard/profile/types";

export interface MedicalInformationSectionProps {
  form: ProfileFormState;
  disabled: boolean;
  onChangeText: (name: ProfileTextFieldName, value: string) => void;
  onChangeDecision: (name: ProfileDecisionFieldName, checked: boolean) => void;
}

export function MedicalInformationSection({
  form,
  disabled,
  onChangeText,
  onChangeDecision,
}: MedicalInformationSectionProps) {
  return (
    <Card aria-labelledby="medical-information-title">
      <CardHeader>
        <CardTitle id="medical-information-title">Información médica</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <TextField
          disabled={disabled}
          id="profile-blood-type"
          label="Tipo de sangre"
          onChange={(value) => onChangeText("blood_type", value)}
          placeholder="Ej: O+"
          value={form.blood_type}
        />

        <fieldset>
          <legend className="text-sm font-medium text-foreground">
            Alergias <span aria-hidden="true" className="text-danger">*</span>
          </legend>
          <TextAreaField
            className="mt-2"
            disabled={disabled}
            id="profile-allergies"
            label="Detalle de alergias"
            none={{
              id: "profile-allergies-none",
              checked: form.allergies_none,
              label: "Sin alergias declaradas",
              onChange: (checked) => onChangeDecision("allergies_none", checked),
              disabled,
            }}
            onChange={(value) => onChangeText("allergies", value)}
            value={form.allergies}
          />
        </fieldset>

        <fieldset>
          <legend className="text-sm font-medium text-foreground">
            Condiciones médicas <span aria-hidden="true" className="text-danger">*</span>
          </legend>
          <TextAreaField
            className="mt-2"
            disabled={disabled}
            id="profile-medical-conditions"
            label="Detalle de condiciones médicas"
            none={{
              id: "profile-medical-conditions-none",
              checked: form.medical_conditions_none,
              label: "Sin condiciones médicas declaradas",
              onChange: (checked) => onChangeDecision("medical_conditions_none", checked),
              disabled,
            }}
            onChange={(value) => onChangeText("medical_conditions", value)}
            value={form.medical_conditions}
          />
        </fieldset>

        <TextAreaField
          disabled={disabled}
          id="profile-medications"
          label="Medicamentos"
          none={{
            id: "profile-medications-none",
            checked: form.medications_none,
            label: "Sin medicamentos declarados",
            onChange: (checked) => onChangeDecision("medications_none", checked),
            disabled,
          }}
          onChange={(value) => onChangeText("medications", value)}
          value={form.medications}
        />

        <TextAreaField
          disabled={disabled}
          id="profile-notes"
          label="Notas"
          onChange={(value) => onChangeText("notes", value)}
          value={form.notes}
        />
      </CardContent>
    </Card>
  );
}
