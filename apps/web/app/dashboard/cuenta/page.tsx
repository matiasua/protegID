"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboardSession } from "@/app/dashboard/dashboard-session-context";
import { logout } from "@/lib/auth";

export default function CuentaPage() {
  const { user, refresh } = useDashboardSession();

  async function handleLogout() {
    await logout();
    await refresh();
  }

  return (
    <>
      <PageHeader
        description="Datos de tu cuenta, verificación de correo y opciones de seguridad."
        title="Cuenta y seguridad"
      />
      <Card>
        <CardContent className="space-y-4 pt-4 sm:pt-5">
          {user ? (
            <div>
              <p className="text-sm font-semibold text-foreground">{user.full_name ?? "Sin nombre informado"}</p>
              <p className="text-sm text-muted-foreground">{user.email}</p>
            </div>
          ) : null}

          <p className="text-sm leading-6 text-muted-foreground">
            Contenido en implementación. Esta pantalla provisional conserva el cierre de sesión mientras se
            construye la versión definitiva.
          </p>

          <Button onClick={() => void handleLogout()} type="button" variant="outline">
            Cerrar sesión
          </Button>
        </CardContent>
      </Card>
    </>
  );
}
