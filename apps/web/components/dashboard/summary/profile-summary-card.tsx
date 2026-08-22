import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  getProfilePublicationStateLabel,
  getProfilePublicationStateVariant,
} from "@/components/dashboard/profile/types";
import type { EmergencyProfile, EmergencyProfileStatus } from "@/types/emergency-profile";

export interface ProfileSummaryCardProps {
  profile: EmergencyProfile | null;
  profileStatus: EmergencyProfileStatus | null;
  isLoading: boolean;
}

export function ProfileSummaryCard({ profile, profileStatus, isLoading }: ProfileSummaryCardProps) {
  return (
    <Card aria-labelledby="profile-summary-title">
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <CardTitle id="profile-summary-title">Perfil de emergencia</CardTitle>
        <StatusBadge
          label={isLoading ? "Consultando..." : getProfilePublicationStateLabel(profile, profileStatus)}
          variant={isLoading ? "neutral" : getProfilePublicationStateVariant(profile, profileStatus)}
        />
      </CardHeader>
      <CardContent>
        <Button asChild variant="outline">
          <Link href="/dashboard/perfil">Gestionar perfil</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
