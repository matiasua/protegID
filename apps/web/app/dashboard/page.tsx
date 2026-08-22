"use client";

import { Suspense, useEffect } from "react";

import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboardSession } from "@/app/dashboard/dashboard-session-context";
import { DeviceStatusSummary } from "@/components/dashboard/summary/device-status-summary";
import { EmailVerificationBanner } from "@/components/dashboard/summary/email-verification-banner";
import { ProfileSummaryCard } from "@/components/dashboard/summary/profile-summary-card";
import { ProtectionStatusCard } from "@/components/dashboard/summary/protection-status-card";
import { aggregateDevicePublicAccess, deriveProtectionStatus } from "@/components/dashboard/summary/derive-protection-status";
import { useDashboardSummary } from "@/components/dashboard/summary/use-dashboard-summary";

function getGreetingTitle(fullName: string | null | undefined): string {
  const trimmedName = fullName?.trim();
  return trimmedName ? `Hola, ${trimmedName}` : "Hola";
}

function DashboardContent() {
  const { user: currentUser } = useDashboardSession();
  const {
    profile,
    profileStatus,
    devices,
    publicAccessByDeviceId,
    isLoadingProfile,
    isLoadingStatus,
    isLoadingDevices,
    profileErrorMessage,
    devicesErrorMessage,
    hasCriticalError,
    load,
  } = useDashboardSummary();

  useEffect(() => {
    if (currentUser) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser]);

  const isProfileLoading = isLoadingProfile || isLoadingStatus;
  const deviceAggregation = aggregateDevicePublicAccess(devices, publicAccessByDeviceId);
  const presentation = deriveProtectionStatus(
    profile,
    profileStatus,
    deviceAggregation,
    profileErrorMessage,
    devicesErrorMessage,
  );

  return (
    <>
      <PageHeader
        description="Tu información de emergencia, en pocos segundos."
        title={getGreetingTitle(currentUser?.full_name)}
      />

      <EmailVerificationBanner currentUser={currentUser} />

      {hasCriticalError ? (
        <p className="rounded-lg border border-danger/30 bg-danger-muted px-4 py-3 text-sm font-medium text-danger" role="alert">
          Tenemos problemas para cargar el estado de tu protección en este momento.{" "}
          <button className="font-semibold underline" onClick={() => void load()} type="button">
            Reintentar
          </button>
        </p>
      ) : currentUser ? (
        <>
          <ProtectionStatusCard isLoading={isProfileLoading} presentation={presentation} />

          <DeviceStatusSummary
            aggregation={deviceAggregation}
            devicesErrorMessage={devicesErrorMessage}
            isLoadingDevices={isLoadingDevices}
          />

          <ProfileSummaryCard isLoading={isProfileLoading} profile={profile} profileStatus={profileStatus} />
        </>
      ) : null}
    </>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardContent />
    </Suspense>
  );
}
