import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/dashboard/page-header";

export default function PerfilPage() {
  return (
    <>
      <PageHeader
        description="Gestiona los datos médicos y de contacto que se muestran en tus identificadores ProtegID."
        title="Perfil de emergencia"
      />
      <Card>
        <CardContent className="pt-4 sm:pt-5">
          <p className="text-sm leading-6 text-muted-foreground">Contenido en implementación.</p>
        </CardContent>
      </Card>
    </>
  );
}
