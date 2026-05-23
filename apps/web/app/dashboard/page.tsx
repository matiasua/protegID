"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import { getMyDevices } from "@/lib/devices";
import { getEmergencyProfile, upsertEmergencyProfile } from "@/lib/emergency-profiles";
import { clearSessionToken, getSessionToken } from "@/lib/session";
import type { AuthUser } from "@/types/auth";
import type { Device } from "@/types/device";
import type { EmergencyProfile, EmergencyProfileInput } from "@/types/emergency-profile";

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

const PROFILE_FIELDS: ProfileFieldConfig[] = [
  { name: "display_name", label: "Nombre visible" },
  { name: "blood_type", label: "Tipo de sangre" },
  { name: "allergies", label: "Alergias", multiline: true },
  { name: "medical_conditions", label: "Condiciones medicas", multiline: true },
  { name: "medications", label: "Medicamentos", multiline: true },
  { name: "emergency_contact_name", label: "Nombre del contacto de emergencia" },
  { name: "emergency_contact_phone", label: "Telefono del contacto de emergencia" },
  { name: "emergency_contact_relationship", label: "Relacion del contacto" },
  { name: "notes", label: "Notas", multiline: true },
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

function getProfileErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiRequestError && (error.status === 401 || error.status === 403)) {
    return "No autorizado para gestionar este perfil de emergencia.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallbackMessage;
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

export default function DashboardPage() {
  const [accessToken, setAccessToken] = useState("");
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileFormState>(() => createEmptyProfileForm());
  const [hasExistingProfile, setHasExistingProfile] = useState<boolean | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deviceErrorMessage, setDeviceErrorMessage] = useState<string | null>(null);
  const [profileErrorMessage, setProfileErrorMessage] = useState<string | null>(null);
  const [profileSuccessMessage, setProfileSuccessMessage] = useState<string | null>(null);
  const [hasCheckedStoredSession, setHasCheckedStoredSession] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);

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

  function resetProfileEditor() {
    setSelectedDevice(null);
    setProfileForm(createEmptyProfileForm());
    setHasExistingProfile(null);
    setProfileErrorMessage(null);
    setProfileSuccessMessage(null);
    setIsLoadingProfile(false);
    setIsSavingProfile(false);
  }

  function resetAuthenticatedState() {
    setCurrentUser(null);
    setDevices([]);
    resetProfileEditor();
  }

  function updateProfileTextField(name: ProfileTextFieldName, value: string) {
    setProfileForm((currentForm) => ({
      ...currentForm,
      [name]: value,
    }));
  }

  async function validateAccessToken(token: string, options: ValidateSessionOptions = {}) {
    setErrorMessage(null);
    setDeviceErrorMessage(null);
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
    } catch (error) {
      setDeviceErrorMessage(getDevicesErrorMessage(error));
    } finally {
      setIsLoadingDevices(false);
    }
  }

  async function handleValidateSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await validateAccessToken(accessToken.trim());
  }

  function handleLogout() {
    clearSessionToken();
    setAccessToken("");
    setErrorMessage(null);
    setDeviceErrorMessage(null);
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
      <section className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">Área privada</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Panel privado ProtegID</h1>
          <p className="mt-4 text-base leading-7 text-slate-600">
            Esta pantalla usa una sesión temporal guardada en sessionStorage durante la sesión del navegador.
            Si no hay sesión activa, inicia sesión o usa el fallback técnico con token manual.
          </p>

          <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <h2 className="text-base font-semibold text-slate-950">Fallback técnico</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Puedes pegar un access token manualmente mientras el flujo de sesión sigue siendo temporal.
            </p>

            <form className="mt-4 space-y-4" onSubmit={handleValidateSession}>
              <div>
                <label className="text-sm font-medium text-slate-700" htmlFor="access-token">
                  Access token
                </label>
                <textarea
                  className="mt-2 min-h-36 w-full resize-y rounded-2xl border border-slate-300 bg-white px-4 py-3 font-mono text-sm text-slate-950 shadow-sm outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                  id="access-token"
                  onChange={(event) => setAccessToken(event.target.value)}
                  placeholder="Pega aquí el access token temporal"
                  value={accessToken}
                />
                <p className="mt-2 text-sm text-slate-500">
                  El token manual se conserva solo en el estado de esta página. No se guarda en localStorage ni cookies.
                </p>
              </div>

              <Button disabled={isValidating || isLoadingDevices} type="submit">
                {isValidating ? "Validando..." : "Validar sesión"}
              </Button>
            </form>
          </div>
        </div>

        <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-xl font-semibold tracking-tight">Estado de sesión</h2>

          {!hasCheckedStoredSession ? (
            <p className="mt-4 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              Revisando sesión temporal...
            </p>
          ) : null}

          {isValidating ? (
            <p className="mt-4 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              Validando token contra la API...
            </p>
          ) : null}

          {errorMessage ? (
            <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
              {errorMessage}
            </p>
          ) : null}

          {currentUser ? (
            <dl className="mt-5 divide-y divide-slate-100 rounded-2xl border border-slate-200">
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Nombre</dt>
                <dd className="text-sm text-slate-950 sm:col-span-2">{currentUser.full_name ?? "Sin nombre informado"}</dd>
              </div>
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Email</dt>
                <dd className="break-words text-sm text-slate-950 sm:col-span-2">{currentUser.email}</dd>
              </div>
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Role</dt>
                <dd className="text-sm text-slate-950 sm:col-span-2">{currentUser.role}</dd>
              </div>
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Status</dt>
                <dd className="text-sm text-slate-950 sm:col-span-2">{currentUser.status}</dd>
              </div>
            </dl>
          ) : null}

          {currentUser ? (
            <Button className="mt-5 w-full" onClick={handleLogout} type="button" variant="outline">
              Cerrar sesión
            </Button>
          ) : null}

          {hasCheckedStoredSession && !isValidating && !currentUser ? (
            <div className="mt-4 space-y-4">
              {!errorMessage ? (
                <p className="text-sm leading-6 text-slate-600">
                  Aún no hay una sesión temporal activa. Inicia sesión para guardar el token en sessionStorage o usa el fallback manual.
                </p>
              ) : null}
              <Button asChild className="w-full">
                <Link href="/login">Ir a login</Link>
              </Button>
            </div>
          ) : null}
        </aside>

        {currentUser ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 lg:col-span-2">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Inventario privado</p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight">Mis dispositivos</h2>
              </div>
            </div>

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

            {!isLoadingDevices && !deviceErrorMessage && devices.length === 0 ? (
              <p className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                No tienes dispositivos asociados.
              </p>
            ) : null}

            {devices.length > 0 ? (
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {devices.map((device) => (
                  <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4" key={device.id}>
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-950">
                          {device.label?.trim() ? device.label : "Sin etiqueta"}
                        </h3>
                        <p className="mt-1 break-words font-mono text-sm text-slate-500">{device.public_id}</p>
                      </div>
                      <span className="mt-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 sm:mt-0">
                        {device.status}
                      </span>
                    </div>

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

                    <div className="mt-4">
                      <Button
                        disabled={isLoadingProfile || isSavingProfile}
                        onClick={() => handleEditProfile(device)}
                        type="button"
                        variant="outline"
                      >
                        Editar perfil
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            ) : null}
          </section>
        ) : null}

        {selectedDevice ? (
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 lg:col-span-2">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Perfil de emergencia</p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight">
                  {selectedDevice.label?.trim() ? selectedDevice.label : "Sin etiqueta"}
                </h2>
                <p className="mt-1 break-words font-mono text-sm text-slate-500">{selectedDevice.public_id}</p>
              </div>
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

            <form className="mt-6 space-y-5" onSubmit={handleSaveProfile}>
              <div className="grid gap-4 md:grid-cols-2">
                {PROFILE_FIELDS.map((field) => (
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

              <label className="flex gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
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

              <Button disabled={isLoadingProfile || isSavingProfile} type="submit">
                {isSavingProfile ? "Guardando..." : "Guardar perfil"}
              </Button>
            </form>
          </section>
        ) : null}
      </section>
    </main>
  );
}
