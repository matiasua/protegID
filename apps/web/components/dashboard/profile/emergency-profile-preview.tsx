import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProfileFormState } from "@/components/dashboard/profile/types";

export interface EmergencyProfilePreviewProps {
  form: ProfileFormState;
}

function renderDecision(text: string, none: boolean, noneLabel: string): string {
  if (none) {
    return noneLabel;
  }

  return text.trim().length > 0 ? text : "Sin información";
}

export function EmergencyProfilePreview({ form }: EmergencyProfilePreviewProps) {
  return (
    <Card aria-labelledby="profile-preview-title" surface="elevated">
      <CardHeader>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Vista previa de tu perfil</p>
        <CardTitle id="profile-preview-title">
          {form.display_name.trim().length > 0 ? form.display_name : "Sin nombre visible"}
        </CardTitle>
        <p className="text-sm leading-6 text-muted-foreground">
          Así podría verse tu información de emergencia si tu perfil se publica en un identificador ProtegID activo.
        </p>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <dl className="grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="font-medium text-muted-foreground">Tipo de sangre</dt>
            <dd className="mt-1 text-foreground">{form.blood_type.trim() || "Sin información"}</dd>
          </div>
          <div>
            <dt className="font-medium text-muted-foreground">Contacto de emergencia</dt>
            <dd className="mt-1 text-foreground">{form.emergency_contact_name.trim() || "Sin información"}</dd>
          </div>
          <div>
            <dt className="font-medium text-muted-foreground">Teléfono de contacto</dt>
            <dd className="mt-1 text-foreground">{form.emergency_contact_phone.trim() || "Sin información"}</dd>
          </div>
          <div>
            <dt className="font-medium text-muted-foreground">Relación</dt>
            <dd className="mt-1 text-foreground">{form.emergency_contact_relationship.trim() || "Sin información"}</dd>
          </div>
        </dl>

        <div>
          <dt className="font-medium text-muted-foreground">Alergias</dt>
          <dd className="mt-1 text-foreground">{renderDecision(form.allergies, form.allergies_none, "Sin alergias declaradas")}</dd>
        </div>

        <div>
          <dt className="font-medium text-muted-foreground">Condiciones médicas</dt>
          <dd className="mt-1 text-foreground">
            {renderDecision(form.medical_conditions, form.medical_conditions_none, "Sin condiciones médicas declaradas")}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-muted-foreground">Medicamentos</dt>
          <dd className="mt-1 text-foreground">
            {renderDecision(form.medications, form.medications_none, "Sin medicamentos declarados")}
          </dd>
        </div>

        {form.notes.trim().length > 0 ? (
          <div>
            <dt className="font-medium text-muted-foreground">Notas</dt>
            <dd className="mt-1 text-foreground">{form.notes}</dd>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
