"use client";

import Link from "next/link";
import { Suspense, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import {
  DashboardSessionProvider,
  useDashboardSession,
} from "@/app/dashboard/dashboard-session-context";
import { logout } from "@/lib/auth";

function DashboardLayoutContent({ children }: { children: ReactNode }) {
  const { user, hasCheckedSession, isValidating, refresh } = useDashboardSession();

  async function handleLogout() {
    await logout();
    await refresh();
  }

  if (!hasCheckedSession || isValidating) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 text-slate-950">
        <p className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          Verificando sesión...
        </p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 text-slate-950">
        <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-sm leading-6 text-slate-600">
            Aún no hay una sesión activa. Inicia sesión para acceder al panel privado.
          </p>
          <Button asChild className="mt-4 w-full">
            <Link href="/login">Ir a login</Link>
          </Button>
        </section>
      </main>
    );
  }

  return (
    <DashboardShell onLogout={() => void handleLogout()} user={user}>
      {children}
    </DashboardShell>
  );
}

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={null}>
      <DashboardSessionProvider>
        <DashboardLayoutContent>{children}</DashboardLayoutContent>
      </DashboardSessionProvider>
    </Suspense>
  );
}
