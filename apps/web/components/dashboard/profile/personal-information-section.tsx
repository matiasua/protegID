import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TextField } from "@/components/dashboard/profile/form-controls";
import type { ProfileFormState } from "@/components/dashboard/profile/types";

export interface PersonalInformationSectionProps {
  form: ProfileFormState;
  disabled: boolean;
  onChangeText: (name: "display_name", value: string) => void;
}

export function PersonalInformationSection({ form, disabled, onChangeText }: PersonalInformationSectionProps) {
  return (
    <Card aria-labelledby="personal-information-title">
      <CardHeader>
        <CardTitle id="personal-information-title">Datos personales</CardTitle>
      </CardHeader>
      <CardContent>
        <TextField
          disabled={disabled}
          helpText="Este nombre se muestra al escanear tu identificador."
          id="profile-display-name"
          label="Nombre visible"
          onChange={(value) => onChangeText("display_name", value)}
          required
          value={form.display_name}
        />
      </CardContent>
    </Card>
  );
}
