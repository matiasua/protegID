"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { DASHBOARD_NAV_ITEMS, isNavItemActive } from "@/components/dashboard/nav-items";

export interface MobileNavProps {
  className?: string;
}

export function MobileNav({ className }: MobileNavProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Navegación principal"
      className={cn("border-t border-border bg-surface pb-[env(safe-area-inset-bottom)]", className)}
    >
      <ul className="flex items-stretch justify-around">
        {DASHBOARD_NAV_ITEMS.map((item) => {
          const active = isNavItemActive(item.href, pathname);
          const Icon = item.icon;

          return (
            <li className="flex-1" key={item.href}>
              <Link
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-[44px] flex-col items-center justify-center gap-1 px-1 py-2 text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset",
                  active ? "text-primary" : "text-muted-foreground",
                )}
                href={item.href}
              >
                <Icon aria-hidden="true" className={cn("h-5 w-5 shrink-0", active ? "text-primary" : "text-muted-foreground")} />
                <span className={active ? "font-semibold" : undefined}>{item.shortLabel}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
