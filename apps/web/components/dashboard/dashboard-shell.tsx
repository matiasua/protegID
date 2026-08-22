"use client";

import type { ReactNode } from "react";

import { DesktopNav } from "@/components/dashboard/desktop-nav";
import { MobileNav } from "@/components/dashboard/mobile-nav";
import type { AuthUser } from "@/types/auth";

export interface DashboardShellProps {
  user: AuthUser | null;
  onLogout: () => void;
  children: ReactNode;
}

export function DashboardShell({ user, onLogout, children }: DashboardShellProps) {
  return (
    <div className="dashboard-theme flex min-h-screen bg-background text-foreground">
      <DesktopNav className="hidden md:flex md:w-60 md:shrink-0" onLogout={onLogout} user={user} />

      <div className="flex min-h-screen flex-1 flex-col">
        <main className="flex-1 px-4 pb-24 pt-6 sm:px-6 md:pb-10 md:pt-8 lg:px-10">
          <div className="mx-auto w-full max-w-[55rem] space-y-6">{children}</div>
        </main>

        <MobileNav className="fixed inset-x-0 bottom-0 z-40 md:hidden" />
      </div>
    </div>
  );
}
