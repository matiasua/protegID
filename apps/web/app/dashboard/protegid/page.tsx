import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/dashboard/page-header";

export default function ProtegidPage() {
  return (
    <>
      <PageHeader
        description="Activa y administra los identificadores físicos vinculados a tu cuenta."
        title="Mis ProtegID"
      />
      <Card>
        <CardContent className="pt-4 sm:pt-5">
          <p className="text-sm leading-6 text-muted-foreground">Contenido en implementación.</p>
        </CardContent>
      </Card>
    </>
  );
}
