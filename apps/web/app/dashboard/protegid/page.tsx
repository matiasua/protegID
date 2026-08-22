"use client";

import { useEffect } from "react";

import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboardSession } from "@/app/dashboard/dashboard-session-context";
import { ActivationCard } from "@/components/dashboard/protegid/activation-card";
import { DeviceList } from "@/components/dashboard/protegid/device-list";
import { isAdminUser } from "@/components/dashboard/protegid/types";
import { useProtegidDevices } from "@/components/dashboard/protegid/use-protegid-devices";
import type { Device } from "@/types/device";

function isEmailVerified(user: ReturnType<typeof useDashboardSession>["user"]): boolean {
  return user?.email_verified_at !== null && user?.email_verified_at !== undefined;
}

export default function ProtegidPage() {
  const { user: currentUser } = useDashboardSession();
  const emailVerified = isEmailVerified(currentUser);
  const isAdmin = isAdminUser(currentUser?.role);

  const {
    devices,
    publicAccessByDeviceId,
    qrStatusByDeviceId,
    isLoadingDevices,
    devicesErrorMessage,
    qrAdminMessage,
    isActivating,
    activationErrorMessage,
    activationSuccessMessage,
    load,
    activate,
    generateQr,
    downloadQr,
    resetActivationMessages,
  } = useProtegidDevices(isAdmin, emailVerified);

  useEffect(() => {
    if (currentUser) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser]);

  const canManageQr = isAdmin && emailVerified && qrAdminMessage === null;

  function handleGenerateQr(device: Device) {
    void generateQr(device);
  }

  function handleDownloadQr(device: Device) {
    void downloadQr(device);
  }

  return (
    <>
      <PageHeader
        description="Activa y administra los identificadores físicos vinculados a tu cuenta."
        title="Mis ProtegID"
      />

      <ActivationCard
        emailVerified={emailVerified}
        errorMessage={activationErrorMessage}
        isActivating={isActivating}
        onActivate={activate}
        onDismissMessages={resetActivationMessages}
        successMessage={activationSuccessMessage}
      />

      {isLoadingDevices ? (
        <p className="rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 text-sm text-primary">
          Cargando identificadores...
        </p>
      ) : null}

      {devicesErrorMessage ? (
        <p className="rounded-lg border border-danger/30 bg-danger-muted px-4 py-3 text-sm font-medium text-danger" role="alert">
          {devicesErrorMessage}
        </p>
      ) : null}

      {qrAdminMessage ? (
        <p className="rounded-lg border border-warning/30 bg-warning-muted px-4 py-3 text-sm text-warning">
          {qrAdminMessage}
        </p>
      ) : null}

      {!isLoadingDevices && !devicesErrorMessage ? (
        <DeviceList
          canManageQr={canManageQr}
          devices={devices}
          emailVerified={emailVerified}
          isAdmin={isAdmin}
          onDownloadQr={handleDownloadQr}
          onGenerateQr={handleGenerateQr}
          publicAccessByDeviceId={publicAccessByDeviceId}
          qrStatusByDeviceId={qrStatusByDeviceId}
        />
      ) : null}
    </>
  );
}
