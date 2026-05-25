"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import { activateDeviceWithClaimCode, getMyDevices } from "@/lib/devices";
import { getEmergencyProfile, upsertEmergencyProfile } from "@/lib/emergency-profiles";
import { createDeviceQr, downloadDeviceQr, getDeviceQrStatus } from "@/lib/qr-codes";
import { clearSessionToken, getSessionToken } from "@/lib/session";
import type { AuthUser } from "@/types/auth";
import type { Device } from "@/types/device";
import type { EmergencyProfile, EmergencyProfileInput } from "@/types/emergency-profile";
import type { DeviceQrStatus } from "@/types/qr-code";

type ProfileFormState = {
  display_name: string;
  blood_type: string;
  allergies: string;
  medical_conditions: string;
  medications: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relationship: string;
  notes: string;
  is_public: boolean;
};

type ProfileTextFieldName = Exclude<keyof ProfileFormState, "is_public">;

type ProfileFieldConfig = {
  name: ProfileTextFieldName;
  label: string;
  multiline?: boolean;
};

type ValidateSessionOptions = {
  clearStoredTokenOnFailure?: boolean;
  updateTokenInput?: boolean;
};

type DeviceQrActionMessage = {
  kind: "success" | "error";
  text: string;
};

type DeviceQrStatusState = {
  isLoading: boolean;
  isGenerating: boolean;
  isDownloading: boolean;
  status: DeviceQrStatus | null;
  hasError: boolean;
  actionMessage: DeviceQrActionMessage | null;
};

type ProfileFieldGroup = {
  title: string;
  fields: ProfileFieldConfig[];
};

const PROFILE_FIELD_GROUPS: ProfileFieldGroup[] = [
  {
    title: "Datos personales",
    fields: [{ name: "display_name", label: "Nombre visible" }],
  },
  {
    title: "Información médica",
    fields: [
      { name: "blood_type", label: "Tipo de sangre" },
      { name: "allergies", label: "Alergias", multiline: true },
      { name: "medical_conditions", label: "Condiciones medicas", multiline: true },
      { name: "medications", label: "Medicamentos", multiline: true },
      { name: "notes", label: "Notas", multiline: true },
    ],
  },
  {
    title: "Contacto de emergencia",
    fields: [
      { name: "emergency_contact_name", label: "Nombre del contacto de emergencia" },
      { name: "emergency_contact_phone", label: "Telefono del contacto de emergencia" },
      { name: "emergency_contact_relationship", label: "Relacion del contacto" },
    ],
  },
];

function getValidationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError && (error.status === 401 || error.status === 403)) {
    return "Token inválido, expirado o sin permisos para acceder al panel.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No se pudo validar la sesión.";
}

function getDevicesErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError && (error.status === 401 || error.status === 403)) {
    return "No autorizado para cargar tus dispositivos.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No se pudieron cargar tus dispositivos.";
}

function getActivationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 400) {
      return "Datos de activación inválidos.";
    }

    if (error.status === 401) {
      return "Sesión expirada o no autenticada.";
    }

    if (error.status === 404) {
      return "Identificador no disponible.";
    }

    if (error.status === 422) {
      return "Código de activación inválido o incompleto.";
    }

    if (error.status === 429) {
      return "Demasiados intentos. Intenta nuevamente más tarde.";
    }
  }

  return "No se pudo activar el identificador.";
}

function getProfileErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiRequestError && (error.status === 401 || error.status === 403)) {
    return "No autorizado para gestionar este perfil de emergencia.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallbackMessage;
}

function getQrGenerationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) {
      return "Sesión expirada o no autenticada.";
    }

    if (error.status === 403) {
      return "La gestión de QR requiere rol admin.";
    }

    if (error.status === 404) {
      return "Dispositivo no encontrado.";
    }
  }

  return "No se pudo generar el QR.";
}

function getQrDownloadErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) {
      return "Sesión expirada o no autenticada.";
    }

    if (error.status === 403) {
      return "La gestión de QR requiere rol admin.";
    }

    if (error.status === 404) {
      return "QR no encontrado. Genera el QR antes de descargarlo.";
    }
  }

  return "No se pudo descargar el QR.";
}

function isAdminUser(user: AuthUser | null): boolean {
  return user?.role.toLowerCase() === "admin";
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

function getQrStatusLabel(qrStatusState: DeviceQrStatusState | undefined): string {
  if (qrStatusState?.isGenerating) {
    return "Generando QR...";
  }

  if (!qrStatusState || qrStatusState.isLoading) {
    return "Consultando QR...";
  }

  if (qrStatusState.hasError) {
    return "QR no disponible";
  }

  return qrStatusState.status?.exists ? "QR generado" : "QR pendiente";
}

function getQrStatusClass(qrStatusState: DeviceQrStatusState | undefined): string {
  if (qrStatusState?.isGenerating) {
    return "border-sky-100 bg-sky-50 text-sky-800";
  }

  if (!qrStatusState || qrStatusState.isLoading) {
    return "border-sky-100 bg-sky-50 text-sky-800";
  }

  if (qrStatusState.hasError) {
    return "border-slate-200 bg-white text-slate-600";
  }

  if (qrStatusState.status?.exists) {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }

  return "border-amber-200 bg-amber-50 text-amber-900";
}

function getQrActionMessageClass(message: DeviceQrActionMessage): string {
  if (message.kind === "success") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }

  return "border-amber-200 bg-amber-50 text-amber-900";
}

function createEmptyProfileForm(): ProfileFormState {
  return {
    display_name: "",
    blood_type: "",
    allergies: "",
    medical_conditions: "",
    medications: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relationship: "",
    notes: "",
    is_public: true,
  };
}

function createProfileForm(profile: EmergencyProfile): ProfileFormState {
  return {
    display_name: profile.display_name ?? "",
    blood_type: profile.blood_type ?? "",
    allergies: profile.allergies ?? "",
    medical_conditions: profile.medical_conditions ?? "",
    medications: profile.medications ?? "",
    emergency_contact_name: profile.emergency_contact_name ?? "",
    emergency_contact_phone: profile.emergency_contact_phone ?? "",
    emergency_contact_relationship: profile.emergency_contact_relationship ?? "",
    notes: profile.notes ?? "",
    is_public: profile.is_public,
  };
}

function normalizeProfileValue(value: string): string | null {
  const normalizedValue = value.trim();
  return normalizedValue.length > 0 ? normalizedValue : null;
}

function createProfilePayload(form: ProfileFormState): EmergencyProfileInput {
  return {
    display_name: normalizeProfileValue(form.display_name),
    blood_type: normalizeProfileValue(form.blood_type),
    allergies: normalizeProfileValue(form.allergies),
    medical_conditions: normalizeProfileValue(form.medical_conditions),
    medications: normalizeProfileValue(form.medications),
    emergency_contact_name: normalizeProfileValue(form.emergency_contact_name),
    emergency_contact_phone: normalizeProfileValue(form.emergency_contact_phone),
    emergency_contact_relationship: normalizeProfileValue(form.emergency_contact_relationship),
    notes: normalizeProfileValue(form.notes),
    is_public: form.is_public,
  };
}

function formatActivatedAt(value: string | null): string {
  if (!value) {
    return "No activado";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getDeviceStatusLabel(status: Device["status"]): string {
  if (status === "pending_activation") {
    return "Pendiente de activación";
  }

  if (status === "active") {
    return "Activo";
  }

  if (status === "disabled") {
    return "Deshabilitado";
  }

  return "Reportado como perdido";
}

function getDeviceStatusDescription(status: Device["status"]): string {
  if (status === "pending_activation") {
    return "Este identificador aún no está vinculado a una cuenta.";
  }

  if (status === "active") {
    return "Este identificador está vinculado a tu cuenta. Completa y publica el perfil para que sea útil al escanearlo.";
  }

  if (status === "disabled") {
    return "Este identificador está deshabilitado y no debería usarse operacionalmente.";
  }

  return "Este identificador fue reportado como perdido. Verifica antes de reutilizarlo.";
}

function getDeviceStatusWarning(status: Device["status"]): string | null {
  if (status === "pending_activation") {
    return "Debe activarse antes de operar con perfil público.";
  }

  if (status === "disabled" || status === "lost") {
    return "Las acciones operacionales están deshabilitadas para este estado.";
  }

  return null;
}

function isDeviceOperational(status: Device["status"]): boolean {
  return status === "active";
}

function getDeviceStatusClass(status: Device["status"]): string {
  if (status === "active") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }

  if (status === "disabled") {
    return "border-slate-200 bg-slate-50 text-slate-700";
  }

  if (status === "lost") {
    return "border-red-200 bg-red-50 text-red-800";
  }

  return "border-amber-200 bg-amber-50 text-amber-900";
}

function DashboardContent() {
  const searchParams = useSearchParams();
  const requestedPublicId = searchParams.get("publicId")?.trim() ?? "";
  const [accessToken, setAccessToken] = useState("");
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [qrStatusByDeviceId, setQrStatusByDeviceId] = useState<Record<string, DeviceQrStatusState>>({});
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [activationPublicId, setActivationPublicId] = useState("");
  const [activationClaimCode, setActivationClaimCode] = useState("");
  const [profileForm, setProfileForm] = useState<ProfileFormState>(() => createEmptyProfileForm());
  const [hasExistingProfile, setHasExistingProfile] = useState<boolean | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deviceErrorMessage, setDeviceErrorMessage] = useState<string | null>(null);
  const [activationErrorMessage, setActivationErrorMessage] = useState<string | null>(null);
  const [activationSuccessMessage, setActivationSuccessMessage] = useState<string | null>(null);
  const [qrAdminMessage, setQrAdminMessage] = useState<string | null>(null);
  const [profileErrorMessage, setProfileErrorMessage] = useState<string | null>(null);
  const [profileSuccessMessage, setProfileSuccessMessage] = useState<string | null>(null);
  const [hasCheckedStoredSession, setHasCheckedStoredSession] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [isActivatingDevice, setIsActivatingDevice] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const currentUserIsAdmin = isAdminUser(currentUser);
  const qrPermissionMessage = currentUserIsAdmin ? qrAdminMessage : null;
  const canManageQr = currentUserIsAdmin && qrPermissionMessage === null;

  useEffect(() => {
    const storedToken = getSessionToken();

    if (!storedToken) {
      setHasCheckedStoredSession(true);
      return;
    }

    void validateAccessToken(storedToken, {
      clearStoredTokenOnFailure: true,
      updateTokenInput: true,
    }).finally(() => setHasCheckedStoredSession(true));
  }, []);

  useEffect(() => {
    if (!requestedPublicId || !currentUser || isLoadingDevices || selectedDevice) {
      return;
    }

    const matchingDevice = devices.find(
      (device) => device.public_id.toLowerCase() === requestedPublicId.toLowerCase(),
    );

    if (matchingDevice) {
      void handleEditProfile(matchingDevice);
    }
  }, [currentUser, devices, isLoadingDevices, requestedPublicId, selectedDevice]);

  function resetProfileEditor() {
    setSelectedDevice(null);
    setProfileForm(createEmptyProfileForm());
    setHasExistingProfile(null);
    setProfileErrorMessage(null);
    setProfileSuccessMessage(null);
    setIsLoadingProfile(false);
    setIsSavingProfile(false);
  }

  function resetActivationForm() {
    setActivationPublicId("");
    setActivationClaimCode("");
    setActivationErrorMessage(null);
    setActivationSuccessMessage(null);
    setIsActivatingDevice(false);
  }

  function resetAuthenticatedState() {
    setCurrentUser(null);
    setDevices([]);
    setQrStatusByDeviceId({});
    setQrAdminMessage(null);
    resetActivationForm();
    resetProfileEditor();
  }

  function updateProfileTextField(name: ProfileTextFieldName, value: string) {
    setProfileForm((currentForm) => ({
      ...currentForm,
      [name]: value,
    }));
  }

  async function validateAccessToken(token: string, options: ValidateSessionOptions = {}) {
    let validatedUser: AuthUser | null = null;

    setErrorMessage(null);
    setDeviceErrorMessage(null);
    setQrAdminMessage(null);
    resetAuthenticatedState();

    if (options.updateTokenInput) {
      setAccessToken(token);
    }

    if (!token) {
      setErrorMessage("Pega un access token antes de validar la sesión.");
      return;
    }

    setIsValidating(true);

    try {
      const user = await getCurrentUser(token);
      validatedUser = user;
      setCurrentUser(user);
    } catch (error) {
      if (options.clearStoredTokenOnFailure) {
        clearSessionToken();
        setAccessToken("");
      }

      setErrorMessage(getValidationErrorMessage(error));
      return;
    } finally {
      setIsValidating(false);
    }

    setIsLoadingDevices(true);

    try {
      const userDevices = await getMyDevices(token);
      setDevices(userDevices);

      if (isAdminUser(validatedUser)) {
        void loadDeviceQrStatuses(userDevices, token);
      } else {
        setQrStatusByDeviceId({});
      }
    } catch (error) {
      setDeviceErrorMessage(getDevicesErrorMessage(error));
    } finally {
      setIsLoadingDevices(false);
    }
  }

  async function loadDeviceQrStatuses(userDevices: Device[], token: string) {
    if (userDevices.length === 0) {
      setQrStatusByDeviceId({});
      return;
    }

    setQrStatusByDeviceId(createInitialQrStatusState(userDevices));

    await Promise.all(
      userDevices.map(async (device) => {
        try {
          const qrStatus = await getDeviceQrStatus(device.id, token);
          setQrStatusByDeviceId((currentStatuses) => ({
            ...currentStatuses,
            [device.id]: {
              isLoading: false,
              isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
              isDownloading: currentStatuses[device.id]?.isDownloading ?? false,
              status: qrStatus,
              hasError: false,
              actionMessage: currentStatuses[device.id]?.actionMessage ?? null,
            },
          }));
        } catch (error) {
          if (error instanceof ApiRequestError && error.status === 403) {
            setQrAdminMessage("La gestión de QR requiere rol admin.");
          }

          setQrStatusByDeviceId((currentStatuses) => ({
            ...currentStatuses,
            [device.id]: {
              isLoading: false,
              isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
              isDownloading: currentStatuses[device.id]?.isDownloading ?? false,
              status: null,
              hasError: true,
              actionMessage: currentStatuses[device.id]?.actionMessage ?? null,
            },
          }));
        }
      }),
    );
  }

  async function handleGenerateDeviceQr(device: Device) {
    const token = accessToken.trim();

    if (!token || !currentUser) {
      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: currentStatuses[device.id]?.isLoading ?? false,
          isGenerating: false,
          isDownloading: false,
          status: currentStatuses[device.id]?.status ?? null,
          hasError: currentStatuses[device.id]?.hasError ?? false,
          actionMessage: {
            kind: "error",
            text: "Sesión expirada o no autenticada.",
          },
        },
      }));
      return;
    }

    if (!isAdminUser(currentUser) || qrAdminMessage !== null) {
      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: currentStatuses[device.id]?.isLoading ?? false,
          isGenerating: false,
          isDownloading: false,
          status: currentStatuses[device.id]?.status ?? null,
          hasError: currentStatuses[device.id]?.hasError ?? false,
          actionMessage: {
            kind: "error",
            text: "La gestión de QR requiere rol admin.",
          },
        },
      }));
      return;
    }

    setQrStatusByDeviceId((currentStatuses) => ({
      ...currentStatuses,
      [device.id]: {
        isLoading: currentStatuses[device.id]?.isLoading ?? false,
        isGenerating: true,
        isDownloading: currentStatuses[device.id]?.isDownloading ?? false,
        status: currentStatuses[device.id]?.status ?? null,
        hasError: currentStatuses[device.id]?.hasError ?? false,
        actionMessage: null,
      },
    }));

    try {
      const qrMetadata = await createDeviceQr(device.id, token);
      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: false,
          isGenerating: false,
          isDownloading: currentStatuses[device.id]?.isDownloading ?? false,
          status: {
            ...qrMetadata,
            exists: true,
          },
          hasError: false,
          actionMessage: {
            kind: "success",
            text: "QR generado correctamente.",
          },
        },
      }));
    } catch (error) {
      const message = getQrGenerationErrorMessage(error);

      if (error instanceof ApiRequestError && error.status === 403) {
        setQrAdminMessage("La gestión de QR requiere rol admin.");
      }

      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: false,
          isGenerating: false,
          isDownloading: currentStatuses[device.id]?.isDownloading ?? false,
          status: currentStatuses[device.id]?.status ?? null,
          hasError: currentStatuses[device.id]?.hasError ?? false,
          actionMessage: {
            kind: "error",
            text: message,
          },
        },
      }));
    }
  }

  async function handleDownloadDeviceQr(device: Device) {
    const token = accessToken.trim();

    if (!token || !currentUser) {
      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: currentStatuses[device.id]?.isLoading ?? false,
          isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
          isDownloading: false,
          status: currentStatuses[device.id]?.status ?? null,
          hasError: currentStatuses[device.id]?.hasError ?? false,
          actionMessage: {
            kind: "error",
            text: "Sesión expirada o no autenticada.",
          },
        },
      }));
      return;
    }

    if (!isAdminUser(currentUser) || qrAdminMessage !== null) {
      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: currentStatuses[device.id]?.isLoading ?? false,
          isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
          isDownloading: false,
          status: currentStatuses[device.id]?.status ?? null,
          hasError: currentStatuses[device.id]?.hasError ?? false,
          actionMessage: {
            kind: "error",
            text: "La gestión de QR requiere rol admin.",
          },
        },
      }));
      return;
    }

    if (!qrStatusByDeviceId[device.id]?.status?.exists) {
      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: currentStatuses[device.id]?.isLoading ?? false,
          isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
          isDownloading: false,
          status: currentStatuses[device.id]?.status ?? null,
          hasError: currentStatuses[device.id]?.hasError ?? false,
          actionMessage: {
            kind: "error",
            text: "QR no encontrado. Genera el QR antes de descargarlo.",
          },
        },
      }));
      return;
    }

    setQrStatusByDeviceId((currentStatuses) => ({
      ...currentStatuses,
      [device.id]: {
        isLoading: currentStatuses[device.id]?.isLoading ?? false,
        isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
        isDownloading: true,
        status: currentStatuses[device.id]?.status ?? null,
        hasError: currentStatuses[device.id]?.hasError ?? false,
        actionMessage: null,
      },
    }));

    try {
      const qrBlob = await downloadDeviceQr(device.id, token);
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

      setQrStatusByDeviceId((currentStatuses) => ({
        ...currentStatuses,
        [device.id]: {
          isLoading: false,
          isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
          isDownloading: false,
          status: currentStatuses[device.id]?.status ?? null,
          hasError: false,
          actionMessage: {
            kind: "success",
            text: "QR descargado correctamente.",
          },
        },
      }));
    } catch (error) {
      const message = getQrDownloadErrorMessage(error);

      if (error instanceof ApiRequestError && error.status === 403) {
        setQrAdminMessage("La gestión de QR requiere rol admin.");
      }

      setQrStatusByDeviceId((currentStatuses) => {
        const currentStatus = currentStatuses[device.id]?.status ?? null;

        return {
          ...currentStatuses,
          [device.id]: {
            isLoading: false,
            isGenerating: currentStatuses[device.id]?.isGenerating ?? false,
            isDownloading: false,
            status: error instanceof ApiRequestError && error.status === 404 && currentStatus
              ? { ...currentStatus, exists: false }
              : currentStatus,
            hasError: currentStatuses[device.id]?.hasError ?? false,
            actionMessage: {
              kind: "error",
              text: message,
            },
          },
        };
      });
    }
  }

  async function handleValidateSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await validateAccessToken(accessToken.trim());
  }

  async function handleActivateIdentifier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = accessToken.trim();
    const publicId = activationPublicId.trim();
    const claimCode = activationClaimCode.trim();

    setActivationErrorMessage(null);
    setActivationSuccessMessage(null);
    setActivationClaimCode("");

    if (!token) {
      setActivationErrorMessage("Sesión expirada o no autenticada.");
      return;
    }

    if (!publicId) {
      setActivationErrorMessage("Ingresa un public_id antes de activar.");
      return;
    }

    if (!claimCode) {
      setActivationErrorMessage("Código de activación inválido o incompleto.");
      return;
    }

    setIsActivatingDevice(true);

    try {
      await activateDeviceWithClaimCode(publicId, claimCode, token);
      setActivationPublicId("");
      setActivationSuccessMessage("Identificador vinculado correctamente. Completa el perfil de emergencia para que sea útil al escanearlo.");

      try {
        const userDevices = await getMyDevices(token);
        setDevices(userDevices);

        if (isAdminUser(currentUser)) {
          void loadDeviceQrStatuses(userDevices, token);
        } else {
          setQrStatusByDeviceId({});
        }
      } catch (error) {
        setDeviceErrorMessage(getDevicesErrorMessage(error));
      }
    } catch (error) {
      setActivationErrorMessage(getActivationErrorMessage(error));
    } finally {
      setIsActivatingDevice(false);
    }
  }

  function handleLogout() {
    clearSessionToken();
    setAccessToken("");
    setErrorMessage(null);
    setDeviceErrorMessage(null);
    setQrAdminMessage(null);
    resetAuthenticatedState();
  }

  async function handleEditProfile(device: Device) {
    const token = accessToken.trim();
    setSelectedDevice(device);
    setProfileForm(createEmptyProfileForm());
    setHasExistingProfile(null);
    setProfileErrorMessage(null);
    setProfileSuccessMessage(null);

    if (!token) {
      setProfileErrorMessage("Valida la sesión antes de editar un perfil.");
      return;
    }

    setIsLoadingProfile(true);

    try {
      const profile = await getEmergencyProfile(device.id, token);

      if (profile === null) {
        setHasExistingProfile(false);
        setProfileForm(createEmptyProfileForm());
        return;
      }

      setHasExistingProfile(true);
      setProfileForm(createProfileForm(profile));
    } catch (error) {
      setProfileErrorMessage(getProfileErrorMessage(error, "No se pudo cargar el perfil de emergencia."));
    } finally {
      setIsLoadingProfile(false);
    }
  }

  async function handleSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (selectedDevice === null) {
      setProfileErrorMessage("Selecciona un dispositivo antes de guardar el perfil.");
      return;
    }

    const token = accessToken.trim();

    if (!token) {
      setProfileErrorMessage("Valida la sesión antes de guardar el perfil.");
      return;
    }

    setProfileErrorMessage(null);
    setProfileSuccessMessage(null);
    setIsSavingProfile(true);

    try {
      const savedProfile = await upsertEmergencyProfile(selectedDevice.id, createProfilePayload(profileForm), token);
      setProfileForm(createProfileForm(savedProfile));
      setHasExistingProfile(true);
      setProfileSuccessMessage("Perfil de emergencia guardado correctamente.");
    } catch (error) {
      setProfileErrorMessage(getProfileErrorMessage(error, "No se pudo guardar el perfil de emergencia."));
    } finally {
      setIsSavingProfile(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8 text-slate-950 sm:px-6 lg:py-12">
      <section className="mx-auto max-w-6xl space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <Link className="inline-flex text-sm font-medium text-sky-700 underline-offset-4 hover:underline" href="/">
                Volver al inicio
              </Link>
              <p className="mt-6 text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">Área privada</p>
              <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Panel privado ProtegID</h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
                Gestiona tus dispositivos y el perfil de emergencia asociado. La sesión sigue siendo temporal y se guarda en sessionStorage durante la sesión del navegador.
              </p>
            </div>

            <span className="w-fit rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-sky-800">
              Sesión temporal
            </span>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="session-status-title">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Estado de sesión</p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight" id="session-status-title">
                Acceso privado
              </h2>
            </div>

            {currentUser ? (
              <Button className="w-full sm:w-auto" onClick={handleLogout} type="button" variant="outline">
                Cerrar sesión
              </Button>
            ) : null}
          </div>

          {!hasCheckedStoredSession ? (
            <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              Revisando sesión temporal...
            </p>
          ) : null}

          {isValidating ? (
            <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              Validando token contra la API...
            </p>
          ) : null}

          {errorMessage ? (
            <p className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
              {errorMessage}
            </p>
          ) : null}

          {currentUser ? (
            <dl className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Nombre</dt>
                <dd className="mt-2 text-sm font-semibold text-slate-950">{currentUser.full_name ?? "Sin nombre informado"}</dd>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Email</dt>
                <dd className="mt-2 break-words text-sm font-semibold text-slate-950">{currentUser.email}</dd>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Role</dt>
                <dd className="mt-2 text-sm font-semibold text-slate-950">{currentUser.role}</dd>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</dt>
                <dd className="mt-2 text-sm font-semibold text-slate-950">{currentUser.status}</dd>
              </div>
            </dl>
          ) : null}

          {hasCheckedStoredSession && !isValidating && !currentUser ? (
            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              {!errorMessage ? (
                <p className="text-sm leading-6 text-slate-600">
                  Aún no hay una sesión temporal activa. Inicia sesión para guardar el token en sessionStorage o usa el fallback manual.
                </p>
              ) : null}
              <Button asChild className="mt-4 w-full sm:w-auto">
                <Link href="/login">Ir a login</Link>
              </Button>
            </div>
          ) : null}

          <details className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-slate-800">Usar token manual</summary>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Puedes pegar un access token manualmente mientras el flujo de sesión sigue siendo temporal.
            </p>

            <form className="mt-4 space-y-4" onSubmit={handleValidateSession}>
              <div>
                <label className="text-sm font-medium text-slate-700" htmlFor="access-token">
                  Access token
                </label>
                <textarea
                  className="mt-2 min-h-32 w-full resize-y rounded-2xl border border-slate-300 bg-white px-4 py-3 font-mono text-sm text-slate-950 shadow-sm outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                  id="access-token"
                  onChange={(event) => setAccessToken(event.target.value)}
                  placeholder="Pega aquí el access token temporal"
                  value={accessToken}
                />
                <p className="mt-2 text-sm text-slate-500">
                  El token manual se conserva solo en el estado de esta página. No se guarda en localStorage ni cookies.
                </p>
              </div>

              <Button disabled={isValidating || isLoadingDevices} type="submit" variant="outline">
                {isValidating ? "Validando..." : "Validar sesión"}
              </Button>
            </form>
          </details>
        </section>

        {currentUser ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="devices-title">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Inventario privado</p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight" id="devices-title">
                  Mis dispositivos
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Selecciona un dispositivo para editar su perfil de emergencia público.
                </p>
              </div>
            </div>

            <section className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4" aria-labelledby="activation-title">
              <div className="max-w-3xl">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Vinculación</p>
                <h3 className="mt-2 text-xl font-bold tracking-tight" id="activation-title">
                  Activar identificador
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Ingresa el public_id del identificador y el código de activación incluido dentro del empaque.
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  El código de activación no se guarda en el navegador.
                </p>
              </div>

              <form className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end" onSubmit={handleActivateIdentifier}>
                <div className="flex-1">
                  <label className="text-sm font-medium text-slate-700" htmlFor="activation-public-id">
                    Public ID
                  </label>
                  <input
                    autoComplete="off"
                    className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 font-mono text-sm uppercase text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                    disabled={isActivatingDevice}
                    id="activation-public-id"
                    onChange={(event) => setActivationPublicId(event.target.value)}
                    placeholder="PID-XXXXXXXXXX"
                    type="text"
                    value={activationPublicId}
                  />
                </div>
                <div className="flex-1">
                  <label className="text-sm font-medium text-slate-700" htmlFor="activation-claim-code">
                    Código de activación
                  </label>
                  <input
                    autoComplete="off"
                    className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 font-mono text-sm uppercase text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                    disabled={isActivatingDevice}
                    id="activation-claim-code"
                    onChange={(event) => setActivationClaimCode(event.target.value)}
                    placeholder="XXXX-XXXX-XXXX"
                    type="text"
                    value={activationClaimCode}
                  />
                </div>
                <Button
                  className="w-full md:w-auto"
                  disabled={
                    isActivatingDevice ||
                    activationPublicId.trim().length === 0 ||
                    activationClaimCode.trim().length === 0
                  }
                  type="submit"
                >
                  {isActivatingDevice ? "Activando..." : "Activar identificador"}
                </Button>
              </form>

              {activationSuccessMessage ? (
                <p className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                  {activationSuccessMessage}
                </p>
              ) : null}

              {activationErrorMessage ? (
                <p className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
                  {activationErrorMessage}
                </p>
              ) : null}
            </section>

            {isLoadingDevices ? (
              <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
                Cargando dispositivos...
              </p>
            ) : null}

            {deviceErrorMessage ? (
              <p className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
                {deviceErrorMessage}
              </p>
            ) : null}

            {qrPermissionMessage ? (
              <p className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                {qrPermissionMessage}
              </p>
            ) : null}

            {!isLoadingDevices && !deviceErrorMessage && devices.length === 0 ? (
              <p className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                No tienes dispositivos asociados.
              </p>
            ) : null}

            {devices.length > 0 ? (
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {devices.map((device) => {
                  const isSelectedDevice = selectedDevice?.id === device.id;
                  const qrStatusState = qrStatusByDeviceId[device.id];
                  const canOperateDevice = isDeviceOperational(device.status);
                  const deviceStatusWarning = getDeviceStatusWarning(device.status);
                  const qrActionButtonLabel = qrStatusState?.isGenerating
                    ? "Generando QR..."
                    : qrStatusState?.status?.exists
                      ? "Regenerar QR"
                      : "Generar QR";
                  const qrDownloadButtonLabel = qrStatusState?.isDownloading ? "Descargando QR..." : "Descargar QR";
                  const isQrActionDisabled = !canManageQr || !canOperateDevice || !qrStatusState || qrStatusState.isLoading || qrStatusState.isGenerating || qrStatusState.isDownloading;
                  const isQrDownloadDisabled =
                    !canManageQr ||
                    !canOperateDevice ||
                    accessToken.trim().length === 0 ||
                    !qrStatusState ||
                    qrStatusState.isLoading ||
                    qrStatusState.isGenerating ||
                    qrStatusState.isDownloading ||
                    qrStatusState.hasError ||
                    !qrStatusState.status?.exists;
                  const shouldShowQrDownloadHelp =
                    canOperateDevice &&
                    qrStatusState !== undefined &&
                    !qrStatusState.isLoading &&
                    !qrStatusState.hasError &&
                    !qrStatusState.status?.exists;
                  const profileVisibilityLabel = isSelectedDevice
                    ? hasExistingProfile === null
                      ? "Consultando perfil"
                      : hasExistingProfile
                        ? profileForm.is_public
                          ? "Perfil público habilitado"
                          : "Perfil no público"
                        : "Perfil pendiente"
                    : "Selecciona Editar perfil para revisar";

                  return (
                    <article
                      className={`rounded-2xl border p-4 transition ${
                        isSelectedDevice ? "border-sky-300 bg-sky-50 shadow-sm" : "border-slate-200 bg-slate-50"
                      }`}
                      key={device.id}
                    >
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-950">
                          {device.label?.trim() ? device.label : "Sin etiqueta"}
                        </h3>
                        <p className="mt-2 rounded-xl border border-slate-200 bg-white px-3 py-2 font-mono text-sm text-slate-700">
                          {device.public_id}
                        </p>
                      </div>
                      <span className={`mt-2 rounded-full border px-3 py-1 text-xs font-semibold sm:mt-0 ${getDeviceStatusClass(device.status)}`}>
                        {getDeviceStatusLabel(device.status)}
                      </span>
                    </div>

                    <p className="mt-4 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-600">
                      {getDeviceStatusDescription(device.status)}
                    </p>

                    {deviceStatusWarning ? (
                      <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
                        {deviceStatusWarning}
                      </p>
                    ) : null}

                    {isSelectedDevice ? (
                      <p className="mt-4 rounded-xl border border-sky-200 bg-white px-3 py-2 text-sm font-medium text-sky-800">
                        Dispositivo seleccionado
                      </p>
                    ) : null}

                    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="font-medium text-slate-500">Tipo</dt>
                        <dd className="mt-1 text-slate-950">{device.device_type}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-slate-500">Activacion</dt>
                        <dd className="mt-1 text-slate-950">{formatActivatedAt(device.activated_at)}</dd>
                      </div>
                    </dl>

                    {!currentUserIsAdmin ? (
                      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                        <h4 className="text-sm font-semibold text-slate-950">Información del identificador</h4>
                        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                          <div>
                            <dt className="font-medium text-slate-500">Public ID</dt>
                            <dd className="mt-1 break-all font-mono text-slate-950">{device.public_id}</dd>
                          </div>
                          <div>
                            <dt className="font-medium text-slate-500">Perfil público</dt>
                            <dd className="mt-1 text-slate-950">{profileVisibilityLabel}</dd>
                          </div>
                        </dl>
                        <p className="mt-3 text-xs leading-5 text-slate-500">
                          Completa el perfil y activa su visibilidad pública para que el QR/NFC muestre información útil.
                        </p>
                      </div>
                    ) : null}

                    {currentUserIsAdmin ? (
                      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <h4 className="text-sm font-semibold text-slate-950">Gestión QR</h4>
                            <p className="mt-1 text-sm leading-6 text-slate-600">
                              Apunta al perfil público <span className="font-mono text-slate-800">/p/{device.public_id}</span>.
                            </p>
                          </div>
                          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold ${getQrStatusClass(qrStatusState)}`}>
                            {getQrStatusLabel(qrStatusState)}
                          </span>
                        </div>

                        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
                          <p>El QR solo contiene la URL pública del perfil. No incluye datos médicos embebidos.</p>
                          <p className="mt-1">La visualización depende de que el perfil esté marcado como público.</p>
                        </div>

                        {qrStatusState?.status?.object_key ? (
                          <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                            <summary className="cursor-pointer font-medium text-slate-700">Detalle técnico</summary>
                            <p className="mt-2 break-all font-mono text-slate-500">{qrStatusState.status.object_key}</p>
                          </details>
                        ) : null}

                        {qrStatusState?.actionMessage ? (
                          <p className={`mt-3 rounded-xl border px-3 py-2 text-sm ${getQrActionMessageClass(qrStatusState.actionMessage)}`}>
                            {qrStatusState.actionMessage.text}
                          </p>
                        ) : null}

                        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                          <Button
                            className="w-full sm:w-auto"
                            disabled={isQrActionDisabled}
                            onClick={() => void handleGenerateDeviceQr(device)}
                            type="button"
                            variant="outline"
                          >
                            {qrActionButtonLabel}
                          </Button>
                          <Button
                            className="w-full sm:w-auto"
                            disabled={isQrDownloadDisabled}
                            onClick={() => void handleDownloadDeviceQr(device)}
                            type="button"
                            variant="outline"
                          >
                            {qrDownloadButtonLabel}
                          </Button>
                        </div>
                        {shouldShowQrDownloadHelp ? (
                          <p className="mt-2 text-xs text-slate-500">Genera el QR antes de descargarlo.</p>
                        ) : null}
                        <p className="mt-2 text-xs leading-5 text-slate-500">
                          La descarga obtiene el PNG desde el backend autenticado. No se expone URL pública de MinIO.
                        </p>
                      </div>
                    ) : null}

                    <div className="mt-5">
                      <Button
                        className="w-full sm:w-auto"
                        disabled={!canOperateDevice || isLoadingProfile || isSavingProfile}
                        onClick={() => handleEditProfile(device)}
                        type="button"
                        variant={isSelectedDevice ? "default" : "outline"}
                      >
                        {isSelectedDevice ? "Editando perfil" : "Editar perfil"}
                      </Button>
                    </div>
                    </article>
                  );
                })}
              </div>
            ) : null}
          </section>
        ) : null}

        {selectedDevice ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="profile-editor-title">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Editor de perfil</p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight" id="profile-editor-title">
                  Perfil de emergencia
                </h2>
                <p className="mt-2 text-sm text-slate-600">
                  Dispositivo seleccionado: <span className="font-mono font-semibold text-slate-950">{selectedDevice.public_id}</span>
                </p>
              </div>

              <span className="w-fit rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
                {selectedDevice.label?.trim() ? selectedDevice.label : "Sin etiqueta"}
              </span>
            </div>

            {isLoadingProfile ? (
              <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
                Cargando perfil de emergencia...
              </p>
            ) : null}

            {!isLoadingProfile && hasExistingProfile === false ? (
              <p className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                Este dispositivo aún no tiene perfil de emergencia.
              </p>
            ) : null}

            {profileErrorMessage ? (
              <p className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
                {profileErrorMessage}
              </p>
            ) : null}

            {profileSuccessMessage ? (
              <p className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                {profileSuccessMessage}
              </p>
            ) : null}

            {isSavingProfile ? (
              <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
                Guardando perfil de emergencia...
              </p>
            ) : null}

            <form className="mt-6 space-y-5" onSubmit={handleSaveProfile}>
              {PROFILE_FIELD_GROUPS.map((group) => (
                <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5" key={group.title}>
                  <h3 className="text-base font-semibold text-slate-950">{group.title}</h3>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    {group.fields.map((field) => (
                      <div className={field.multiline ? "md:col-span-2" : undefined} key={field.name}>
                        <label className="text-sm font-medium text-slate-700" htmlFor={`profile-${field.name}`}>
                          {field.label}
                        </label>
                        {field.multiline ? (
                          <textarea
                            className="mt-2 min-h-28 w-full resize-y rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 shadow-sm outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                            disabled={isLoadingProfile || isSavingProfile}
                            id={`profile-${field.name}`}
                            onChange={(event) => updateProfileTextField(field.name, event.target.value)}
                            value={profileForm[field.name]}
                          />
                        ) : (
                          <input
                            className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 shadow-sm outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                            disabled={isLoadingProfile || isSavingProfile}
                            id={`profile-${field.name}`}
                            onChange={(event) => updateProfileTextField(field.name, event.target.value)}
                            type="text"
                            value={profileForm[field.name]}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              ))}

              <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5">
                <h3 className="text-base font-semibold text-slate-950">Visibilidad pública</h3>
                <label className="mt-4 flex gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                  <input
                    checked={profileForm.is_public}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-700"
                    disabled={isLoadingProfile || isSavingProfile}
                    onChange={(event) =>
                      setProfileForm((currentForm) => ({
                        ...currentForm,
                        is_public: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-semibold text-slate-950">Perfil público habilitado</span>
                    <span className="mt-1 block text-slate-600">
                      Controla si este perfil se muestra en /p/{selectedDevice.public_id}.
                    </span>
                  </span>
                </label>
              </section>

              <Button className="w-full sm:w-auto" disabled={isLoadingProfile || isSavingProfile} type="submit">
                {isSavingProfile ? "Guardando..." : "Guardar perfil"}
              </Button>
            </form>
          </section>
        ) : null}
      </section>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardContent />
    </Suspense>
  );
}
