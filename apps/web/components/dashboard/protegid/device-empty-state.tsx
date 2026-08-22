import { Card, CardContent } from "@/components/ui/card";

export function DeviceEmptyState() {
  return (
    <Card>
      <CardContent className="pt-4 text-sm leading-6 text-muted-foreground sm:pt-5">
        Aún no tienes ProtegID asociados. Actívalo con el Public ID y el código de activación incluidos con el
        producto físico.
      </CardContent>
    </Card>
  );
}
