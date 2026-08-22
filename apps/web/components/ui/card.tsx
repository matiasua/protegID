import * as React from "react";

import { cn } from "@/lib/utils";

const cardSurfaceVariants = {
  default: "bg-surface border-border",
  elevated: "bg-surface-elevated border-border",
  primary: "bg-surface border-primary/40",
  success: "bg-success-muted border-success/30",
  warning: "bg-warning-muted border-warning/30",
  danger: "bg-danger-muted border-danger/30",
} as const;

export type CardSurface = keyof typeof cardSurfaceVariants;

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  surface?: CardSurface;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(({ className, surface = "default", ...props }, ref) => (
  <div
    className={cn("rounded-lg border text-card-foreground shadow-sm", cardSurfaceVariants[surface], className)}
    ref={ref}
    {...props}
  />
));
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div className={cn("flex flex-col gap-1.5 p-4 sm:p-5", className)} ref={ref} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 className={cn("text-lg font-semibold leading-none tracking-tight text-foreground", className)} ref={ref} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p className={cn("text-sm leading-6 text-muted-foreground", className)} ref={ref} {...props} />
  ),
);
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div className={cn("p-4 pt-0 sm:p-5 sm:pt-0", className)} ref={ref} {...props} />,
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div className={cn("flex items-center gap-3 p-4 pt-0 sm:p-5 sm:pt-0", className)} ref={ref} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
