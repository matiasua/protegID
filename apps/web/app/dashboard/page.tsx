"use client";

import Link from "next/link";
import { Suspense, type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { getCurrentUser, logout, resendVerification } from "@/lib/auth";
import { activateDeviceWithClaimCode, getDevicePublicAccessStatus, getMyDevices } from "@/lib/devices";
import { getEmergencyProfile, getEmergencyProfileStatus, updateEmergencyProfile } from "@/lib/emergency-profiles";
import { createDeviceQr, downloadDeviceQr, getDeviceQrStatus } from "@/lib/qr-codes";
import type { AuthUser } from "@/types/auth";
import type { Device } from "@/types/device";
import type {
  EmergencyProfile,
  EmergencyProfileInput,
  EmergencyProfileStatus,
  PublicAccessStatus,
} from "@/types/emergency-profile";
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
  medical_conditions_none: boolean;
  allergies_none: boolean;
  medications_none: boolean;
  public_consent_accepted_at: string | null;
  public_consent_version: string | null;
};

type ProfileTextFieldName =
  | "display_name"
  | "blood_type"
  | "allergies"
  | "medical_conditions"
  | "medications"
  | "emergency_contact_name"
  | "emergency_contact_phone"
  | "emergency_contact_relationship"
  | "notes";

type ProfileDecisionFieldName = "medical_conditions_none" | "allergies_none" | "medications_none";

type ProfileFieldConfig = {
  name: ProfileTextFieldName;
  label: string;
  multiline?: boolean;
  noneField?: ProfileDecisionFieldName;
  noneLabel?: string;
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

type PublicAccessStatusState = {
  isLoading: boolean;
  status: PublicAccessStatus | null;
  hasError: boolean;
};

type ProfileFieldGroup = {
  title: string;
  fields: ProfileFieldConfig[];
};

type ResendVerificationStatus = "idle" | "sending" | "sent" | "error";

const EMAIL_VERIFICATION_REQUIRED_MESSAGE = "Debes verificar tu correo antes de realizar esta acción.";

const PROFILE_FIELD_GROUPS: ProfileFieldGroup[] = [
  {
    title: "Datos personales",
    fields: [{ name: "display_name", label: "Nombre visible" }],
  },
  {
    title: "Información médica",
    fields: [
      { name: "blood_type", label: "Tipo de sangre" },
      {
        name: "allergies",
        label: "Alergias",
        multiline: true,
        noneField: "allergies_none",
        noneLabel: "Sin alergias declaradas",
      },
      {
        name: "medical_conditions",
        label: "Condiciones medicas",
        multiline: true,
        noneField: "medical_conditions_none",
        noneLabel: "Sin condiciones medicas declaradas",
      },
      {
        name: "medications",
        label: "Medicamentos",
        multiline: true,
        noneField: "medications_none",
        noneLabel: "Sin medicamentos declarados",
      },
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
    return "Sesión inválida, expirada o sin permisos para acceder al panel.";
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

    if (error.status === 403) {
      return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
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
  if (error instanceof ApiRequestError && error.status === 401) {
    return "No autorizado para gestionar este perfil de emergencia.";
  }

  if (error instanceof ApiRequestError && error.status === 403) {
    return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
  }

  if (error instanceof ApiRequestError && error.status === 409) {
    return "Error de integridad del perfil de emergencia. Contacta a soporte.";
  }

  if (error instanceof ApiRequestError && error.status === 422) {
    return "Completa los campos obligatorios antes de publicar el perfil.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallbackMessage;
}

function getReadinessFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    display_name: "Nombre visible",
    emergency_contact_name: "Nombre del contacto de emergencia",
    emergency_contact_phone: "Telefono del contacto de emergencia",
    medical_conditions_decision: "Declarar condiciones medicas o marcar que no hay",
    allergies_decision: "Declarar alergias o marcar que no hay",
  };

  return labels[field] ?? field;
}

function getPublicAccessBlockingReasonLabel(reason: string): string {
  const labels: Record<string, string> = {
    device_missing: "Identificador no disponible.",
    device_not_active: "El identificador debe estar activo.",
    device_deleted: "El identificador no esta operativo.",
    protected_person_missing: "No hay un perfil de emergencia asociado a esta cuenta.",
    protected_person_deleted: "La cuenta protegida no esta disponible.",
    profile_missing: "Aun no existe perfil de emergencia.",
    profile_deleted: "El perfil de emergencia no esta operativo.",
    profile_private: "El perfil de emergencia no esta marcado como publico.",
    publication_not_eligible: "El perfil de emergencia no cumple los requisitos para publicarse.",
  };

  return labels[reason] ?? reason;
}

/**
 * Estado de publicacion del perfil (cuenta), independiente de cualquier
 * Device: A) incompleto, B) listo pero sin consentimiento vigente,
 * C) elegible pero privado, D) publico.
 */
function getProfilePublicationStateLabel(
  profile: EmergencyProfile | null,
  profileStatus: EmergencyProfileStatus | null,
): string {
  if (!profileStatus) {
    return "Consultando perfil";
  }

  if (!profileStatus.readiness.is_ready) {
    return "Perfil incompleto";
  }

  if (!profileStatus.publication_eligibility.consent_valid) {
    return "Perfil listo, falta consentimiento vigente";
  }

  if (!profile?.is_public) {
    return "Perfil listo para publicar (privado)";
  }

  return "Perfil publico";
}

function getProfilePublicationStateClass(
  profile: EmergencyProfile | null,
  profileStatus: EmergencyProfileStatus | null,
): string {
  if (!profileStatus || !profileStatus.readiness.is_ready) {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }

  if (!profileStatus.publication_eligibility.consent_valid) {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }

  if (profile?.is_public) {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }

  return "border-sky-200 bg-sky-50 text-sky-800";
}

function isConsentAccepted(form: ProfileFormState, profileStatus: EmergencyProfileStatus | null): boolean {
  return Boolean(
    form.public_consent_accepted_at &&
      form.public_consent_version &&
      (!profileStatus || form.public_consent_version === profileStatus.publication_eligibility.consent_version),
  );
}

function getQrGenerationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401) {
      return "Sesión expirada o no autenticada.";
    }

    if (error.status === 403) {
      return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
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
      return EMAIL_VERIFICATION_REQUIRED_MESSAGE;
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

function isEmailVerified(user: AuthUser | null): boolean {
  return user?.email_verified_at !== null && user?.email_verified_at !== undefined;
}

function getResendVerificationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }

  return "No se pudo reenviar el correo de verificación.";
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

function createInitialPublicAccessState(devices: Device[]): Record<string, PublicAccessStatusState> {
  return Object.fromEntries(
    devices.map<[string, PublicAccessStatusState]>((device) => [
      device.id,
      {
        isLoading: true,
        status: null,
        hasError: false,
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

function getPublicAccessStatusLabel(state: PublicAccessStatusState | undefined): string {
  if (!state || state.isLoading) {
    return "Consultando identificador...";
  }

  if (state.hasError) {
    return "Estado no disponible";
  }

  return state.status?.is_operational ? "Operativo" : "Requiere atención";
}

function getPublicAccessStatusClass(state: PublicAccessStatusState | undefined): string {
  if (!state || state.isLoading) {
    return "border-sky-100 bg-sky-50 text-sky-800";
  }

  if (state.hasError) {
    return "border-slate-200 bg-white text-slate-600";
  }

  return state.status?.is_operational
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : "border-amber-200 bg-amber-50 text-amber-900";
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
    is_public: false,
    medical_conditions_none: false,
    allergies_none: false,
    medications_none: false,
    public_consent_accepted_at: null,
    public_consent_version: null,
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
    medical_conditions_none: profile.medical_conditions_none,
    allergies_none: profile.allergies_none,
    medications_none: profile.medications_none,
    public_consent_accepted_at: profile.public_consent_accepted_at,
    public_consent_version: profile.public_consent_version,
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
    allergies: form.allergies_none ? null : normalizeProfileValue(form.allergies),
    medical_conditions: form.medical_conditions_none ? null : normalizeProfileValue(form.medical_conditions),
    medications: form.medications_none ? null : normalizeProfileValue(form.medications),
    emergency_contact_name: normalizeProfileValue(form.emergency_contact_name),
    emergency_contact_phone: normalizeProfileValue(form.emergency_contact_phone),
    emergency_contact_relationship: normalizeProfileValue(form.emergency_contact_relationship),
    notes: normalizeProfileValue(form.notes),
    is_public: form.is_public,
    medical_conditions_none: form.medical_conditions_none,
    allergies_none: form.allergies_none,
    medications_none: form.medications_none,
    public_consent_accepted_at: form.public_consent_accepted_at,
    public_consent_version: form.public_consent_version,
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
    return "Este identificador está vinculado a tu cuenta y puede mostrar tu perfil de emergencia si esta publicado.";
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
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [qrStatusByDeviceId, setQrStatusByDeviceId] = useState<Record<string, DeviceQrStatusState>>({});
  const [publicAccessByDeviceId, setPublicAccessByDeviceId] = useState<Record<string, PublicAccessStatusState>>({});
  const [activationPublicId, setActivationPublicId] = useState("");
  const [activationClaimCode, setActivationClaimCode] = useState("");
  const [profile, setProfile] = useState<EmergencyProfile | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileFormState>(() => createEmptyProfileForm());
  const [profileStatus, setProfileStatus] = useState<EmergencyProfileStatus | null>(null);
  const [hasExistingProfile, setHasExistingProfile] = useState<boolean | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deviceErrorMessage, setDeviceErrorMessage] = useState<string | null>(null);
  const [activationErrorMessage, setActivationErrorMessage] = useState<string | null>(null);
  const [activationSuccessMessage, setActivationSuccessMessage] = useState<string | null>(null);
  const [qrAdminMessage, setQrAdminMessage] = useState<string | null>(null);
  const [profileErrorMessage, setProfileErrorMessage] = useState<string | null>(null);
  const [profileSuccessMessage, setProfileSuccessMessage] = useState<string | null>(null);
  const [resendVerificationStatus, setResendVerificationStatus] = useState<ResendVerificationStatus>("idle");
  const [resendVerificationMessage, setResendVerificationMessage] = useState<string | null>(null);
  const [hasCheckedSession, setHasCheckedSession] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [isActivatingDevice, setIsActivatingDevice] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isLoadingProfileStatus, setIsLoadingProfileStatus] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const currentUserIsAdmin = isAdminUser(currentUser);
  const currentUserEmailVerified = isEmailVerified(currentUser);
  const qrPermissionMessage = currentUserIsAdmin ? qrAdminMessage : null;
  const canManageQr = currentUserIsAdmin && currentUserEmailVerified && qrPermissionMessage === null;

  useEffect(() => {
    void loadAuthenticatedDashboard().finally(() => setHasCheckedSession(true));
  }, []);

  function resetProfileEditor() {
    setProfile(null);
    setProfileForm(createEmptyProfileForm());
    setProfileStatus(null);
    setHasExistingProfile(null);
    setProfileErrorMessage(null);
    setProfileSuccessMessage(null);
    setIsLoadingProfile(false);
    setIsLoadingProfileStatus(false);
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
    setPublicAccessByDeviceId({});
    setQrAdminMessage(null);
    setResendVerificationStatus("idle");
    setResendVerificationMessage(null);
    resetActivationForm();
    resetProfileEditor();
  }

  function updateProfileTextField(name: ProfileTextFieldName, value: string) {
    setProfileForm((currentForm) => ({
      ...currentForm,
      [name]: value,
    }));
  }

  function updateProfileDecisionField(name: ProfileDecisionFieldName, checked: boolean) {
    setProfileForm((currentForm) => {
      const nextForm = { ...currentForm, [name]: checked };

      if (checked && name === "medical_conditions_none") {
        nextForm.medical_conditions = "";
      }

      if (checked && name === "allergies_none") {
        nextForm.allergies = "";
      }

      if (checked && name === "medications_none") {
        nextForm.medications = "";
      }

      return nextForm;
    });
  }

  function updateConsentAccepted(checked: boolean) {
    setProfileForm((currentForm) => ({
      ...currentForm,
      is_public: checked ? currentForm.is_public : false,
      public_consent_accepted_at: checked ? new Date().toISOString() : null,
      public_consent_version: checked
        ? profileStatus?.publication_eligibility.consent_version ?? currentForm.public_consent_version
        : null,
    }));
  }

  async function loadAuthenticatedDashboard() {
    let validatedUser: AuthUser | null = null;

    setErrorMessage(null);
    setDeviceErrorMessage(null);
    setQrAdminMessage(null);
    resetAuthenticatedState();

    setIsValidating(true);

    try {
      const user = await getCurrentUser();
      validatedUser = user;
      setCurrentUser(user);
    } catch (error) {
      setErrorMessage(getValidationErrorMessage(error));
      return;
    } finally {
      setIsValidating(false);
    }

    void loadProfile();

    setIsLoadingDevices(true);

    try {
      const userDevices = await getMyDevices();
      setDevices(userDevices);
      void loadPublicAccessStatuses(userDevices);

      if (isAdminUser(validatedUser)) {
        void loadDeviceQrStatuses(userDevices, isEmailVerified(validatedUser));
      } else {
        setQrStatusByDeviceId({});
      }
    } catch (error) {
      setDeviceErrorMessage(getDevicesErrorMessage(error));
    } finally {
      setIsLoadingDevices(false);
    }
  }

  async function loadProfile() {
    setProfileErrorMessage(null);
    setProfileSuccessMessage(null);
    setIsLoadingProfile(true);
    setIsLoadingProfileStatus(true);

    try {
      const [loadedProfile, loadedStatus] = await Promise.all([
        getEmergencyProfile(),
        getEmergencyProfileStatus(),
      ]);

      setProfileStatus(loadedStatus);

      if (loadedProfile === null) {
        setHasExistingProfile(false);
        setProfileForm(createEmptyProfileForm());
        return;
      }

      setProfile(loadedProfile);
      setHasExistingProfile(true);
      setProfileForm(createProfileForm(loadedProfile));
    } catch (error) {
      setProfileErrorMessage(getProfileErrorMessage(error, "No se pudo cargar el perfil de emergencia."));
    } finally {
      setIsLoadingProfile(false);
      setIsLoadingProfileStatus(false);
    }
  }

  async function loadPublicAccessStatuses(userDevices: Device[]) {
    if (userDevices.length === 0) {
      setPublicAccessByDeviceId({});
      return;
    }

    setPublicAccessByDeviceId(createInitialPublicAccessState(userDevices));

    await Promise.all(
      userDevices.map(async (device) => {
        try {
          const status = await getDevicePublicAccessStatus(device.id);
          setPublicAccessByDeviceId((currentStatuses) => ({
            ...currentStatuses,
            [device.id]: {
              isLoading: false,
              status,
              hasError: false,
            },
          }));
        } catch {
          setPublicAccessByDeviceId((currentStatuses) => ({
            ...currentStatuses,
            [device.id]: {
              isLoading: false,
              status: null,
              hasError: true,
            },
          }));
        }
      }),
    );
  }

  async function loadDeviceQrStatuses(userDevices: Device[], emailVerified = currentUserEmailVerified) {
    if (userDevices.length === 0) {
      setQrStatusByDeviceId({});
      return;
    }

    setQrStatusByDeviceId(createInitialQrStatusState(userDevices));

    await Promise.all(
      userDevices.map(async (device) => {
        try {
          const qrStatus = await getDeviceQrStatus(device.id);
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
            setQrAdminMessage(emailVerified ? "La gestión de QR requiere rol admin." : EMAIL_VERIFICATION_REQUIRED_MESSAGE);
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
    if (!currentUser) {
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

    if (!isEmailVerified(currentUser)) {
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
            text: EMAIL_VERIFICATION_REQUIRED_MESSAGE,
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
      const qrMetadata = await createDeviceQr(device.id);
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
        setQrAdminMessage(currentUserEmailVerified ? "La gestión de QR requiere rol admin." : EMAIL_VERIFICATION_REQUIRED_MESSAGE);
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
    if (!currentUser) {
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

    if (!isEmailVerified(currentUser)) {
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
            text: EMAIL_VERIFICATION_REQUIRED_MESSAGE,
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

  async function handleActivateIdentifier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const publicId = activationPublicId.trim();
    const claimCode = activationClaimCode.trim();

    setActivationErrorMessage(null);
    setActivationSuccessMessage(null);
    setActivationClaimCode("");

    if (!currentUser) {
      setActivationErrorMessage("Sesión expirada o no autenticada.");
      return;
    }

    if (!isEmailVerified(currentUser)) {
      setActivationErrorMessage(EMAIL_VERIFICATION_REQUIRED_MESSAGE);
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
      await activateDeviceWithClaimCode(publicId, claimCode);
      setActivationPublicId("");
      setActivationSuccessMessage("Identificador vinculado correctamente. Tu perfil de emergencia se mostrará en él si está publicado.");

      try {
        const userDevices = await getMyDevices();
        setDevices(userDevices);
        void loadPublicAccessStatuses(userDevices);

        if (isAdminUser(currentUser)) {
          void loadDeviceQrStatuses(userDevices, isEmailVerified(currentUser));
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

  async function handleLogout() {
    await logout();
    setErrorMessage(null);
    setDeviceErrorMessage(null);
    setQrAdminMessage(null);
    resetAuthenticatedState();
  }

  async function handleSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!currentUser) {
      setProfileErrorMessage("Inicia sesión antes de guardar el perfil.");
      return;
    }

    if (!isEmailVerified(currentUser)) {
      setProfileErrorMessage(EMAIL_VERIFICATION_REQUIRED_MESSAGE);
      return;
    }

    setProfileErrorMessage(null);
    setProfileSuccessMessage(null);
    setIsSavingProfile(true);

    try {
      const savedProfile = await updateEmergencyProfile(createProfilePayload(profileForm));
      const status = await getEmergencyProfileStatus();
      setProfile(savedProfile);
      setProfileForm(createProfileForm(savedProfile));
      setProfileStatus(status);
      setHasExistingProfile(true);
      setProfileSuccessMessage(
        savedProfile.is_public && status.publication_eligibility.can_publish
          ? "Perfil publicado. Los identificadores activos ya pueden mostrar tu ficha de emergencia."
          : "Perfil de emergencia guardado correctamente.",
      );
      void loadPublicAccessStatuses(devices);
    } catch (error) {
      setProfileErrorMessage(getProfileErrorMessage(error, "No se pudo guardar el perfil de emergencia."));
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleResendVerification() {
    setResendVerificationStatus("sending");
    setResendVerificationMessage(null);

    try {
      const response = await resendVerification();
      setResendVerificationStatus("sent");
      setResendVerificationMessage(
        response.verification_sent
          ? "Correo de verificación reenviado. Revisa tu bandeja de entrada."
          : "Tu correo ya figura como verificado.",
      );
    } catch (error) {
      setResendVerificationStatus("error");
      setResendVerificationMessage(getResendVerificationErrorMessage(error));
    }
  }

  const readinessCompletedCount = profileStatus
    ? profileStatus.readiness.required_fields.length - profileStatus.readiness.missing_fields.length
    : 0;
  const readinessRequiredCount = profileStatus?.readiness.required_fields.length ?? 0;
  const profileConsentAccepted = isConsentAccepted(profileForm, profileStatus);

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
                Gestiona tu perfil de emergencia y tus identificadores ProtegID. La sesión se mantiene con una cookie HttpOnly emitida por el backend.
              </p>
            </div>

            <span className="w-fit rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-sky-800">
              Sesión segura
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
              <Button className="w-full sm:w-auto" onClick={() => void handleLogout()} type="button" variant="outline">
                Cerrar sesión
              </Button>
            ) : null}
          </div>

          {!hasCheckedSession ? (
            <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              Revisando sesión...
            </p>
          ) : null}

          {isValidating ? (
            <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              Validando sesión contra la API...
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
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Verificación email</dt>
                <dd className="mt-2 text-sm font-semibold text-slate-950">
                  {currentUserEmailVerified ? "Verificado" : "Pendiente"}
                </dd>
              </div>
            </dl>
          ) : null}

          {currentUser && !currentUserEmailVerified ? (
            <section className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950" aria-labelledby="email-verification-title">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="font-semibold" id="email-verification-title">Tu correo aún no está verificado.</h3>
                  <p className="mt-2 leading-6">
                    Verifica tu correo para activar identificadores, editar tu perfil de emergencia y publicarlo.
                  </p>
                </div>
                <Button
                  className="w-full sm:w-auto"
                  disabled={resendVerificationStatus === "sending"}
                  onClick={() => void handleResendVerification()}
                  type="button"
                  variant="outline"
                >
                  {resendVerificationStatus === "sending" ? "Enviando..." : "Reenviar correo de verificación"}
                </Button>
              </div>
              {resendVerificationMessage ? (
                <p className={`mt-4 rounded-xl border px-3 py-2 font-medium ${resendVerificationStatus === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-emerald-200 bg-white text-emerald-800"}`}>
                  {resendVerificationMessage}
                </p>
              ) : null}
            </section>
          ) : null}

          {hasCheckedSession && !isValidating && !currentUser ? (
            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              {!errorMessage ? (
                <p className="text-sm leading-6 text-slate-600">
                  Aún no hay una sesión activa. Inicia sesión para acceder al panel privado.
                </p>
              ) : null}
              <Button asChild className="mt-4 w-full sm:w-auto">
                <Link href="/login">Ir a login</Link>
              </Button>
            </div>
          ) : null}
        </section>

        {currentUser ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="devices-title">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Inventario privado</p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight" id="devices-title">
                  Mis ProtegID
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Cada identificador muestra tu único perfil de emergencia cuando está activo, publicado y operativo.
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

              {!currentUserEmailVerified ? (
                <p className="mt-4 rounded-2xl border border-amber-200 bg-white px-4 py-3 text-sm font-medium text-amber-900">
                  Debes verificar tu correo antes de activar este identificador.
                </p>
              ) : null}

              <form className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end" onSubmit={handleActivateIdentifier}>
                <div className="flex-1">
                  <label className="text-sm font-medium text-slate-700" htmlFor="activation-public-id">
                    Public ID
                  </label>
                  <input
                    autoComplete="off"
                    className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 font-mono text-sm uppercase text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                    disabled={isActivatingDevice || !currentUserEmailVerified}
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
                    disabled={isActivatingDevice || !currentUserEmailVerified}
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
                    !currentUserEmailVerified ||
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
                  const qrStatusState = qrStatusByDeviceId[device.id];
                  const publicAccessState = publicAccessByDeviceId[device.id];
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

                  return (
                    <article
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition"
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

                    <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h4 className="text-sm font-semibold text-slate-950">Acceso público a tu ficha</h4>
                          <p className="mt-1 text-sm leading-6 text-slate-600">
                            Public ID: <span className="font-mono text-slate-800">{device.public_id}</span>
                          </p>
                        </div>
                        <span className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold ${getPublicAccessStatusClass(publicAccessState)}`}>
                          {getPublicAccessStatusLabel(publicAccessState)}
                        </span>
                      </div>

                      {publicAccessState?.status && publicAccessState.status.blocking_reasons.length > 0 ? (
                        <ul className="mt-3 space-y-1 text-xs text-amber-800">
                          {publicAccessState.status.blocking_reasons.map((reason) => (
                            <li key={reason}>{getPublicAccessBlockingReasonLabel(reason)}</li>
                          ))}
                        </ul>
                      ) : null}
                    </div>

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

                        {!currentUserEmailVerified ? (
                          <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
                            Debes verificar tu correo antes de realizar esta acción.
                          </p>
                        ) : null}

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
                    </article>
                  );
                })}
              </div>
            ) : null}
          </section>
        ) : null}

        {currentUser ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" aria-labelledby="profile-editor-title">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Editor de perfil</p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight" id="profile-editor-title">
                  Mi perfil de emergencia
                </h2>
                <p className="mt-2 text-sm text-slate-600">
                  Un único perfil de emergencia por cuenta. Se muestra en cualquiera de tus identificadores ProtegID activos que esté publicado.
                </p>
              </div>
            </div>

            {isLoadingProfile ? (
              <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
                Cargando perfil de emergencia...
              </p>
            ) : null}

            {!isLoadingProfile && hasExistingProfile === false ? (
              <p className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                Aún no has completado tu perfil de emergencia.
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

            <section className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5" aria-labelledby="profile-readiness-title">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Preparacion del perfil</p>
                  <h3 className="mt-2 text-xl font-bold tracking-tight" id="profile-readiness-title">
                    Estado del perfil
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    El backend decide si el perfil puede publicarse. Esta tarjeta solo muestra el avance para completarlo.
                  </p>
                </div>
                <span className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold ${getProfilePublicationStateClass(profile, profileStatus)}`}>
                  {isLoadingProfileStatus ? "Consultando perfil" : getProfilePublicationStateLabel(profile, profileStatus)}
                </span>
              </div>

              {profileStatus ? (
                <div className="mt-4 space-y-4">
                  <div>
                    <div className="flex items-center justify-between gap-3 text-sm font-medium text-slate-700">
                      <span>Campos obligatorios</span>
                      <span>{readinessCompletedCount}/{readinessRequiredCount}</span>
                    </div>
                    <div className="mt-2 h-3 overflow-hidden rounded-full bg-white ring-1 ring-slate-200">
                      <div
                        className="h-full rounded-full bg-sky-600 transition-all"
                        style={{ width: `${readinessRequiredCount > 0 ? (readinessCompletedCount / readinessRequiredCount) * 100 : 0}%` }}
                      />
                    </div>
                  </div>

                  {profileStatus.publication_eligibility.can_publish && profile?.is_public ? (
                    <p className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                      Perfil publico: tus identificadores activos pueden mostrar tu ficha de emergencia.
                    </p>
                  ) : null}

                  {profileStatus.readiness.missing_fields.length > 0 ? (
                    <div className="rounded-2xl border border-amber-200 bg-white p-4">
                      <h4 className="text-sm font-semibold text-amber-950">Campos faltantes</h4>
                      <ul className="mt-3 space-y-2 text-sm text-amber-900">
                        {profileStatus.readiness.missing_fields.map((field) => (
                          <li key={field}>{getReadinessFieldLabel(field)}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {profileStatus.readiness.is_ready && !profileStatus.publication_eligibility.consent_valid ? (
                    <div className="rounded-2xl border border-slate-200 bg-white p-4">
                      <h4 className="text-sm font-semibold text-slate-950">Pendiente</h4>
                      <p className="mt-2 text-sm text-slate-700">
                        Falta aceptar el consentimiento de publicación vigente (versión {profileStatus.publication_eligibility.consent_version}).
                      </p>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="mt-4 rounded-2xl border border-sky-100 bg-white px-4 py-3 text-sm text-sky-800">
                  {isLoadingProfileStatus ? "Consultando estado del perfil..." : "No se pudo consultar el estado del perfil."}
                </p>
              )}
            </section>

            {!currentUserEmailVerified ? (
              <p className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
                Debes verificar tu correo antes de realizar esta acción.
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
                            disabled={isLoadingProfile || isSavingProfile || !currentUserEmailVerified || (field.noneField ? profileForm[field.noneField] : false)}
                            id={`profile-${field.name}`}
                            onChange={(event) => updateProfileTextField(field.name, event.target.value)}
                            value={profileForm[field.name]}
                          />
                        ) : (
                          <input
                            className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 shadow-sm outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                            disabled={isLoadingProfile || isSavingProfile || !currentUserEmailVerified || (field.noneField ? profileForm[field.noneField] : false)}
                            id={`profile-${field.name}`}
                            onChange={(event) => updateProfileTextField(field.name, event.target.value)}
                            type="text"
                            value={profileForm[field.name]}
                          />
                        )}
                        {field.noneField && field.noneLabel ? (
                          <label className="mt-3 flex gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                            <input
                              checked={profileForm[field.noneField]}
                              className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-700"
                              disabled={isLoadingProfile || isSavingProfile || !currentUserEmailVerified}
                              onChange={(event) => updateProfileDecisionField(field.noneField as ProfileDecisionFieldName, event.target.checked)}
                              type="checkbox"
                            />
                            <span>{field.noneLabel}</span>
                          </label>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </section>
              ))}

              <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5">
                <h3 className="text-base font-semibold text-slate-950">Consentimiento y visibilidad publica</h3>
                <label className="mt-4 flex gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                  <input
                    checked={profileConsentAccepted}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-700"
                    disabled={isLoadingProfile || isSavingProfile || !profileStatus || !currentUserEmailVerified}
                    onChange={(event) => updateConsentAccepted(event.target.checked)}
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-semibold text-slate-950">Acepto la publicacion de mi ficha de emergencia</span>
                    <span className="mt-1 block text-slate-600">
                      Acepto que ProtegID muestre publicamente mi informacion de emergencia al escanear el QR/NFC de cualquiera de mis identificadores fisicos activos.
                    </span>
                    {profileStatus ? (
                      <span className="mt-2 block text-xs text-slate-500">Version de consentimiento: {profileStatus.publication_eligibility.consent_version}</span>
                    ) : null}
                  </span>
                </label>

                <label className="mt-4 flex gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                  <input
                    checked={profileForm.is_public}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-700"
                    disabled={isLoadingProfile || isSavingProfile || !currentUserEmailVerified}
                    onChange={(event) =>
                      setProfileForm((currentForm) => ({
                        ...currentForm,
                        is_public: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="block font-semibold text-slate-950">Habilitar perfil publico</span>
                    <span className="mt-1 block text-slate-600">
                      Controla si tu perfil se muestra en tus identificadores ProtegID activos. El backend solo lo publicara si cumple los minimos y el consentimiento vigente.
                    </span>
                    {profileStatus && !profileStatus.publication_eligibility.can_publish ? (
                      <span className="mt-2 block text-xs font-medium text-amber-700">
                        El perfil aun no esta listo para publicarse. Puedes guardar avances sin habilitarlo.
                      </span>
                    ) : null}
                  </span>
                </label>
              </section>

              <Button className="w-full sm:w-auto" disabled={isLoadingProfile || isSavingProfile || !currentUserEmailVerified} type="submit">
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
