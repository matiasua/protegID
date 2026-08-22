import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AuthUser } from "@/types/auth";

export interface SessionCardProps {
  user: AuthUser;
  onLogout: () => void;
}

export function SessionCard({ user, onLogout }: SessionCardProps) {
  return (
    <Card aria-labelledby="session-title">
      <CardHeader className="space-y-0">
        <CardTitle id="session-title">Sesión</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Conectado como <span className="font-medium text-foreground">{user.email}</span>.
        </p>
        <Button className="w-full sm:w-auto" onClick={onLogout} type="button" variant="outline">
          Cerrar sesión
        </Button>
      </CardContent>
    </Card>
  );
}
