import { LayoutDashboard, ShieldCheck, Smartphone, UserRound } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type DashboardNavItem = {
  href: "/dashboard" | "/dashboard/perfil" | "/dashboard/protegid" | "/dashboard/cuenta";
  label: string;
  shortLabel: string;
  icon: LucideIcon;
};

export const DASHBOARD_NAV_ITEMS: DashboardNavItem[] = [
  { href: "/dashboard", label: "Resumen", shortLabel: "Resumen", icon: LayoutDashboard },
  { href: "/dashboard/perfil", label: "Perfil de emergencia", shortLabel: "Perfil", icon: UserRound },
  { href: "/dashboard/protegid", label: "Mis ProtegID", shortLabel: "ProtegID", icon: Smartphone },
  { href: "/dashboard/cuenta", label: "Cuenta y seguridad", shortLabel: "Cuenta", icon: ShieldCheck },
];

export function isNavItemActive(itemHref: DashboardNavItem["href"], pathname: string): boolean {
  if (itemHref === "/dashboard") {
    return pathname === "/dashboard";
  }

  return pathname === itemHref || pathname.startsWith(`${itemHref}/`);
}
