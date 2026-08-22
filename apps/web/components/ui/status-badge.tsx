import type { LucideIcon } from "lucide-react";
import { AlertTriangle, CheckCircle2, Circle, Info, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

const STATUS_BADGE_VARIANTS = {
  neutral: {
    className: "border-border bg-surface-muted text-muted-foreground",
    icon: Circle,
  },
  info: {
    className: "border-primary/30 bg-primary/10 text-primary",
    icon: Info,
  },
  success: {
    className: "border-success/30 bg-success-muted text-success",
    icon: CheckCircle2,
  },
  warning: {
    className: "border-warning/30 bg-warning-muted text-warning",
    icon: AlertTriangle,
  },
  danger: {
    className: "border-danger/30 bg-danger-muted text-danger",
    icon: XCircle,
  },
} as const satisfies Record<string, { className: string; icon: LucideIcon }>;

export type StatusBadgeVariant = keyof typeof STATUS_BADGE_VARIANTS;

export interface StatusBadgeProps {
  variant: StatusBadgeVariant;
  label: string;
  icon?: LucideIcon;
  className?: string;
}

export function StatusBadge({ variant, label, icon, className }: StatusBadgeProps) {
  const { className: variantClassName, icon: DefaultIcon } = STATUS_BADGE_VARIANTS[variant];
  const Icon = icon ?? DefaultIcon;

  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold",
        variantClassName,
        className,
      )}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
      <span>{label}</span>
    </span>
  );
}
