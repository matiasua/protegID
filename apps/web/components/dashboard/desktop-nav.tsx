"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { DASHBOARD_NAV_ITEMS, isNavItemActive } from "@/components/dashboard/nav-items";
import type { AuthUser } from "@/types/auth";

export interface DesktopNavProps {
  user: AuthUser | null;
  onLogout: () => void;
  className?: string;
}

export function DesktopNav({ user, onLogout, className }: DesktopNavProps) {
  const pathname = usePathname();

  return (
    <aside className={cn("flex-col border-r border-border bg-surface", className)}>
      <div className="px-5 py-6">
        <span className="text-sm font-bold tracking-tight text-foreground">ProtegID</span>
        <p className="text-caption mt-1">Panel privado</p>
      </div>

      <nav aria-label="Navegación principal" className="flex-1 px-3">
        <ul className="space-y-1">
          {DASHBOARD_NAV_ITEMS.map((item) => {
            const active = isNavItemActive(item.href, pathname);
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
                    active
                      ? "bg-primary/15 text-primary"
                      : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
                  )}
                  href={item.href}
                >
                  <Icon aria-hidden="true" className="h-4.5 w-4.5 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-border-subtle px-5 py-4">
        {user ? (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">{user.full_name ?? "Sin nombre informado"}</p>
            <p className="truncate text-caption">{user.email}</p>
          </div>
        ) : null}
        <button
          className="mt-3 w-full rounded-md px-3 py-2 text-left text-sm font-medium text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={onLogout}
          type="button"
        >
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
