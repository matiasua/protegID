import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { isAdminUser } from "@/components/dashboard/protegid/types";
import type { AuthUser } from "@/types/auth";

export interface AccountInformationCardProps {
  user: AuthUser;
}

export function AccountInformationCard({ user }: AccountInformationCardProps) {
  return (
    <Card aria-labelledby="account-information-title">
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <CardTitle id="account-information-title">Información de la cuenta</CardTitle>
        {isAdminUser(user.role) ? <StatusBadge label="Administrador" variant="info" /> : null}
      </CardHeader>
      <CardContent className="space-y-1">
        <p className="text-sm font-semibold text-foreground">{user.full_name ?? "Sin nombre informado"}</p>
        <p className="text-sm text-muted-foreground">{user.email}</p>
      </CardContent>
    </Card>
  );
}
