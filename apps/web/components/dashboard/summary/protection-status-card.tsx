import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, Circle, Info, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, type CardSurface } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  ProtectionStatusPresentation,
  ProtectionStatusVariant,
} from "@/components/dashboard/summary/derive-protection-status";

const VARIANT_ICON: Record<ProtectionStatusVariant, LucideIcon> = {
  neutral: Circle,
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
};

const VARIANT_SURFACE: Record<ProtectionStatusVariant, CardSurface> = {
  neutral: "default",
  info: "primary",
  success: "success",
  warning: "warning",
  danger: "danger",
};

const VARIANT_ICON_CLASS: Record<ProtectionStatusVariant, string> = {
  neutral: "text-muted-foreground",
  info: "text-primary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

export interface ProtectionStatusCardProps {
  presentation: ProtectionStatusPresentation;
  isLoading: boolean;
}

export function ProtectionStatusCard({ presentation, isLoading }: ProtectionStatusCardProps) {
  const Icon = VARIANT_ICON[presentation.variant];

  return (
    <Card aria-labelledby="protection-status-title" surface={VARIANT_SURFACE[presentation.variant]}>
      <CardHeader className="flex-row items-start gap-3 space-y-0">
        <Icon aria-hidden="true" className={cn("mt-0.5 h-6 w-6 shrink-0", VARIANT_ICON_CLASS[presentation.variant])} />
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Estado de tu protección</p>
          <CardTitle className="mt-1" id="protection-status-title">
            {isLoading ? "Consultando el estado de tu protección..." : presentation.headline}
          </CardTitle>
        </div>
      </CardHeader>
      {!isLoading && (presentation.description || presentation.primaryCta || presentation.secondaryCta) ? (
        <CardContent className="space-y-4">
          {presentation.description ? (
            <p className="text-sm leading-6 text-muted-foreground">{presentation.description}</p>
          ) : null}
          {presentation.primaryCta || presentation.secondaryCta ? (
            <div className="flex flex-wrap gap-3">
              {presentation.primaryCta ? (
                <Button asChild>
                  <Link href={presentation.primaryCta.href}>{presentation.primaryCta.label}</Link>
                </Button>
              ) : null}
              {presentation.secondaryCta ? (
                <Button asChild variant="outline">
                  <Link href={presentation.secondaryCta.href}>{presentation.secondaryCta.label}</Link>
                </Button>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  );
}
