"use client";

import { useCallback, useState } from "react";

import { getDevicesErrorMessage } from "@/components/dashboard/protegid/types";
import { getProfileErrorMessage } from "@/components/dashboard/profile/types";
import { getDevicePublicAccessStatus, getMyDevices } from "@/lib/devices";
import { getEmergencyProfile, getEmergencyProfileStatus } from "@/lib/emergency-profiles";
import type { Device } from "@/types/device";
import type { EmergencyProfile, EmergencyProfileStatus, PublicAccessStatus } from "@/types/emergency-profile";

/**
 * Hook de solo lectura para el Resumen (/dashboard). No realiza mutaciones,
 * no carga QR, no carga estado de activación ni datos admin. No debe
 * reutilizarse para operaciones — es exclusivo para presentar el estado
 * ya existente en el backend.
 */

export type PublicAccessStatusState = {
  isLoading: boolean;
  status: PublicAccessStatus | null;
  hasError: boolean;
};

function createInitialPublicAccessState(devices: Device[]): Record<string, PublicAccessStatusState> {
  return Object.fromEntries(
    devices.map<[string, PublicAccessStatusState]>((device) => [
      device.id,
      { isLoading: true, status: null, hasError: false },
    ]),
  );
}

export function useDashboardSummary() {
  const [profile, setProfile] = useState<EmergencyProfile | null>(null);
  const [profileStatus, setProfileStatus] = useState<EmergencyProfileStatus | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [publicAccessByDeviceId, setPublicAccessByDeviceId] = useState<Record<string, PublicAccessStatusState>>({});

  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);

  const [profileErrorMessage, setProfileErrorMessage] = useState<string | null>(null);
  const [statusErrorMessage, setStatusErrorMessage] = useState<string | null>(null);
  const [devicesErrorMessage, setDevicesErrorMessage] = useState<string | null>(null);

  const loadPublicAccessStatuses = useCallback(async (userDevices: Device[]) => {
    if (userDevices.length === 0) {
      setPublicAccessByDeviceId({});
      return;
    }

    setPublicAccessByDeviceId(createInitialPublicAccessState(userDevices));

    await Promise.all(
      userDevices.map(async (device) => {
        try {
          const status = await getDevicePublicAccessStatus(device.id);
          setPublicAccessByDeviceId((current) => ({
            ...current,
            [device.id]: { isLoading: false, status, hasError: false },
          }));
        } catch {
          setPublicAccessByDeviceId((current) => ({
            ...current,
            [device.id]: { isLoading: false, status: null, hasError: true },
          }));
        }
      }),
    );
  }, []);

  const load = useCallback(async () => {
    setIsLoadingProfile(true);
    setIsLoadingStatus(true);
    setIsLoadingDevices(true);
    setProfileErrorMessage(null);
    setStatusErrorMessage(null);
    setDevicesErrorMessage(null);

    const [profileResult, statusResult, devicesResult] = await Promise.allSettled([
      getEmergencyProfile(),
      getEmergencyProfileStatus(),
      getMyDevices(),
    ]);

    if (profileResult.status === "fulfilled") {
      setProfile(profileResult.value);
    } else {
      setProfile(null);
      setProfileErrorMessage(getProfileErrorMessage(profileResult.reason, "No se pudo consultar el perfil de emergencia."));
    }
    setIsLoadingProfile(false);

    if (statusResult.status === "fulfilled") {
      setProfileStatus(statusResult.value);
    } else {
      setProfileStatus(null);
      setStatusErrorMessage(getProfileErrorMessage(statusResult.reason, "No se pudo consultar el estado del perfil."));
    }
    setIsLoadingStatus(false);

    if (devicesResult.status === "fulfilled") {
      setDevices(devicesResult.value);
      setIsLoadingDevices(false);
      void loadPublicAccessStatuses(devicesResult.value);
    } else {
      setDevices([]);
      setPublicAccessByDeviceId({});
      setDevicesErrorMessage(getDevicesErrorMessage(devicesResult.reason));
      setIsLoadingDevices(false);
    }
  }, [loadPublicAccessStatuses]);

  const hasCriticalError = Boolean(statusErrorMessage && devicesErrorMessage && profileErrorMessage);

  return {
    profile,
    profileStatus,
    devices,
    publicAccessByDeviceId,
    isLoadingProfile,
    isLoadingStatus,
    isLoadingDevices,
    profileErrorMessage,
    statusErrorMessage,
    devicesErrorMessage,
    hasCriticalError,
    load,
  };
}
