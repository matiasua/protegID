"use client";

import { useCallback, useState } from "react";

import { ApiRequestError } from "@/lib/api";
import { activateDeviceWithClaimCode, getDevicePublicAccessStatus, getMyDevices } from "@/lib/devices";
import { createDeviceQr, downloadDeviceQr, getDeviceQrStatus } from "@/lib/qr-codes";
import type { Device } from "@/types/device";
import type { PublicAccessStatus } from "@/types/emergency-profile";
import type { DeviceQrStatus } from "@/types/qr-code";
import {
  EMAIL_VERIFICATION_REQUIRED_MESSAGE,
  getActivationErrorMessage,
  getDevicesErrorMessage,
  getQrDownloadErrorMessage,
  getQrGenerationErrorMessage,
} from "@/components/dashboard/protegid/types";

export type DeviceQrActionMessage = {
  kind: "success" | "error";
  text: string;
};

export type DeviceQrStatusState = {
  isLoading: boolean;
  isGenerating: boolean;
  isDownloading: boolean;
  status: DeviceQrStatus | null;
  hasError: boolean;
  actionMessage: DeviceQrActionMessage | null;
};

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

function createInitialQrStatusState(devices: Device[]): Record<string, DeviceQrStatusState> {
  return Object.fromEntries(
    devices.map<[string, DeviceQrStatusState]>((device) => [
      device.id,
      {
        isLoading: true,
        isGenerating: false,
        isDownloading: false,
        status: null,
        hasError: false,
        actionMessage: null,
      },
    ]),
  );
}

export function useProtegidDevices(isAdmin: boolean, emailVerified: boolean) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [publicAccessByDeviceId, setPublicAccessByDeviceId] = useState<Record<string, PublicAccessStatusState>>({});
  const [qrStatusByDeviceId, setQrStatusByDeviceId] = useState<Record<string, DeviceQrStatusState>>({});
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [devicesErrorMessage, setDevicesErrorMessage] = useState<string | null>(null);
  const [qrAdminMessage, setQrAdminMessage] = useState<string | null>(null);
  const [isActivating, setIsActivating] = useState(false);
  const [activationErrorMessage, setActivationErrorMessage] = useState<string | null>(null);
  const [activationSuccessMessage, setActivationSuccessMessage] = useState<string | null>(null);

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

  const loadQrStatuses = useCallback(
    async (userDevices: Device[]) => {
      if (!isAdmin) {
        setQrStatusByDeviceId({});
        return;
      }

      if (userDevices.length === 0) {
        setQrStatusByDeviceId({});
        return;
      }

      setQrStatusByDeviceId(createInitialQrStatusState(userDevices));

      await Promise.all(
        userDevices.map(async (device) => {
          try {
            const status = await getDeviceQrStatus(device.id);
            setQrStatusByDeviceId((current) => ({
              ...current,
              [device.id]: {
                isLoading: false,
                isGenerating: current[device.id]?.isGenerating ?? false,
                isDownloading: current[device.id]?.isDownloading ?? false,
                status,
                hasError: false,
                actionMessage: current[device.id]?.actionMessage ?? null,
              },
            }));
          } catch (error) {
            if (error instanceof ApiRequestError && error.status === 403) {
              setQrAdminMessage(emailVerified ? "La gestión de QR requiere rol admin." : EMAIL_VERIFICATION_REQUIRED_MESSAGE);
            }

            setQrStatusByDeviceId((current) => ({
              ...current,
              [device.id]: {
                isLoading: false,
                isGenerating: current[device.id]?.isGenerating ?? false,
                isDownloading: current[device.id]?.isDownloading ?? false,
                status: null,
                hasError: true,
                actionMessage: current[device.id]?.actionMessage ?? null,
              },
            }));
          }
        }),
      );
    },
    [isAdmin, emailVerified],
  );

  const load = useCallback(async () => {
    setDevicesErrorMessage(null);
    setQrAdminMessage(null);
    setIsLoadingDevices(true);

    try {
      const userDevices = await getMyDevices();
      setDevices(userDevices);
      void loadPublicAccessStatuses(userDevices);
      void loadQrStatuses(userDevices);
    } catch (error) {
      setDevicesErrorMessage(getDevicesErrorMessage(error));
    } finally {
      setIsLoadingDevices(false);
    }
  }, [loadPublicAccessStatuses, loadQrStatuses]);

  const activate = useCallback(
    async (publicId: string, claimCode: string) => {
      setActivationErrorMessage(null);
      setActivationSuccessMessage(null);

      if (!emailVerified) {
        setActivationErrorMessage(EMAIL_VERIFICATION_REQUIRED_MESSAGE);
        return false;
      }

      if (!publicId) {
        setActivationErrorMessage("Ingresa un public_id antes de activar.");
        return false;
      }

      if (!claimCode) {
        setActivationErrorMessage("Código de activación inválido o incompleto.");
        return false;
      }

      setIsActivating(true);

      try {
        await activateDeviceWithClaimCode(publicId, claimCode);
        setActivationSuccessMessage(
          "Identificador vinculado correctamente. Tu perfil de emergencia se mostrará en él si está publicado.",
        );

        try {
          const userDevices = await getMyDevices();
          setDevices(userDevices);
          void loadPublicAccessStatuses(userDevices);
          void loadQrStatuses(userDevices);
        } catch (error) {
          setDevicesErrorMessage(getDevicesErrorMessage(error));
        }

        return true;
      } catch (error) {
        setActivationErrorMessage(getActivationErrorMessage(error));
        return false;
      } finally {
        setIsActivating(false);
      }
    },
    [emailVerified, loadPublicAccessStatuses, loadQrStatuses],
  );

  const generateQr = useCallback(
    async (device: Device) => {
      if (!isAdmin || qrAdminMessage !== null) {
        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: current[device.id]?.isLoading ?? false,
            isGenerating: false,
            isDownloading: current[device.id]?.isDownloading ?? false,
            status: current[device.id]?.status ?? null,
            hasError: current[device.id]?.hasError ?? false,
            actionMessage: { kind: "error", text: "La gestión de QR requiere rol admin." },
          },
        }));
        return;
      }

      if (!emailVerified) {
        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: current[device.id]?.isLoading ?? false,
            isGenerating: false,
            isDownloading: current[device.id]?.isDownloading ?? false,
            status: current[device.id]?.status ?? null,
            hasError: current[device.id]?.hasError ?? false,
            actionMessage: { kind: "error", text: EMAIL_VERIFICATION_REQUIRED_MESSAGE },
          },
        }));
        return;
      }

      setQrStatusByDeviceId((current) => ({
        ...current,
        [device.id]: {
          isLoading: current[device.id]?.isLoading ?? false,
          isGenerating: true,
          isDownloading: current[device.id]?.isDownloading ?? false,
          status: current[device.id]?.status ?? null,
          hasError: current[device.id]?.hasError ?? false,
          actionMessage: null,
        },
      }));

      try {
        const qrMetadata = await createDeviceQr(device.id);
        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: false,
            isGenerating: false,
            isDownloading: current[device.id]?.isDownloading ?? false,
            status: { ...qrMetadata, exists: true },
            hasError: false,
            actionMessage: { kind: "success", text: "QR generado correctamente." },
          },
        }));
      } catch (error) {
        const message = getQrGenerationErrorMessage(error);

        if (error instanceof ApiRequestError && error.status === 403) {
          setQrAdminMessage(emailVerified ? "La gestión de QR requiere rol admin." : EMAIL_VERIFICATION_REQUIRED_MESSAGE);
        }

        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: false,
            isGenerating: false,
            isDownloading: current[device.id]?.isDownloading ?? false,
            status: current[device.id]?.status ?? null,
            hasError: current[device.id]?.hasError ?? false,
            actionMessage: { kind: "error", text: message },
          },
        }));
      }
    },
    [isAdmin, emailVerified, qrAdminMessage],
  );

  const downloadQr = useCallback(
    async (device: Device) => {
      if (!isAdmin || qrAdminMessage !== null) {
        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: current[device.id]?.isLoading ?? false,
            isGenerating: current[device.id]?.isGenerating ?? false,
            isDownloading: false,
            status: current[device.id]?.status ?? null,
            hasError: current[device.id]?.hasError ?? false,
            actionMessage: { kind: "error", text: "La gestión de QR requiere rol admin." },
          },
        }));
        return;
      }

      if (!emailVerified) {
        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: current[device.id]?.isLoading ?? false,
            isGenerating: current[device.id]?.isGenerating ?? false,
            isDownloading: false,
            status: current[device.id]?.status ?? null,
            hasError: current[device.id]?.hasError ?? false,
            actionMessage: { kind: "error", text: EMAIL_VERIFICATION_REQUIRED_MESSAGE },
          },
        }));
        return;
      }

      if (!qrStatusByDeviceId[device.id]?.status?.exists) {
        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: current[device.id]?.isLoading ?? false,
            isGenerating: current[device.id]?.isGenerating ?? false,
            isDownloading: false,
            status: current[device.id]?.status ?? null,
            hasError: current[device.id]?.hasError ?? false,
            actionMessage: { kind: "error", text: "QR no encontrado. Genera el QR antes de descargarlo." },
          },
        }));
        return;
      }

      setQrStatusByDeviceId((current) => ({
        ...current,
        [device.id]: {
          isLoading: current[device.id]?.isLoading ?? false,
          isGenerating: current[device.id]?.isGenerating ?? false,
          isDownloading: true,
          status: current[device.id]?.status ?? null,
          hasError: current[device.id]?.hasError ?? false,
          actionMessage: null,
        },
      }));

      try {
        const qrBlob = await downloadDeviceQr(device.id);
        const objectUrl = URL.createObjectURL(qrBlob);
        const link = document.createElement("a");

        try {
          link.href = objectUrl;
          link.download = `${device.public_id}.png`;
          document.body.appendChild(link);
          link.click();
        } finally {
          link.remove();
          URL.revokeObjectURL(objectUrl);
        }

        setQrStatusByDeviceId((current) => ({
          ...current,
          [device.id]: {
            isLoading: false,
            isGenerating: current[device.id]?.isGenerating ?? false,
            isDownloading: false,
            status: current[device.id]?.status ?? null,
            hasError: false,
            actionMessage: { kind: "success", text: "QR descargado correctamente." },
          },
        }));
      } catch (error) {
        const message = getQrDownloadErrorMessage(error);

        if (error instanceof ApiRequestError && error.status === 403) {
          setQrAdminMessage("La gestión de QR requiere rol admin.");
        }

        setQrStatusByDeviceId((current) => {
          const currentStatus = current[device.id]?.status ?? null;

          return {
            ...current,
            [device.id]: {
              isLoading: false,
              isGenerating: current[device.id]?.isGenerating ?? false,
              isDownloading: false,
              status:
                error instanceof ApiRequestError && error.status === 404 && currentStatus
                  ? { ...currentStatus, exists: false }
                  : currentStatus,
              hasError: current[device.id]?.hasError ?? false,
              actionMessage: { kind: "error", text: message },
            },
          };
        });
      }
    },
    [isAdmin, emailVerified, qrAdminMessage, qrStatusByDeviceId],
  );

  const resetActivationMessages = useCallback(() => {
    setActivationErrorMessage(null);
    setActivationSuccessMessage(null);
  }, []);

  return {
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
  };
}
