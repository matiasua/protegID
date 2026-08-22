"use client";

import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboardSession } from "@/app/dashboard/dashboard-session-context";
import { AccountInformationCard } from "@/components/dashboard/account/account-information-card";
import { EmailVerificationCard } from "@/components/dashboard/account/email-verification-card";
import { SessionCard } from "@/components/dashboard/account/session-card";
import { logout } from "@/lib/auth";

export default function CuentaPage() {
  const { user, refresh } = useDashboardSession();

  async function handleLogout() {
    await logout();
    await refresh();
  }

  if (!user) {
    return null;
  }

  return (
    <>
      <PageHeader description="Datos de tu cuenta y verificación de correo." title="Cuenta y seguridad" />

      <AccountInformationCard user={user} />
      <EmailVerificationCard user={user} />
      <SessionCard onLogout={() => void handleLogout()} user={user} />
    </>
  );
}
