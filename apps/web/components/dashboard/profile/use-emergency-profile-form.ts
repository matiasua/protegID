"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  getEmergencyProfile,
  getEmergencyProfileStatus,
  updateEmergencyProfile,
} from "@/lib/emergency-profiles";
import type { EmergencyProfile, EmergencyProfileStatus } from "@/types/emergency-profile";
import {
  createEmptyProfileForm,
  createProfileForm,
  createProfilePayload,
  getProfileErrorMessage,
  type ProfileDecisionFieldName,
  type ProfileFormState,
  type ProfileTextFieldName,
} from "@/components/dashboard/profile/types";

export type ProfileSaveStatus = "initial" | "dirty" | "saving" | "saved" | "error";

function areFormsEqual(a: ProfileFormState, b: ProfileFormState): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function useEmergencyProfileForm(enabled: boolean, emailVerified: boolean) {
  const [profile, setProfile] = useState<EmergencyProfile | null>(null);
  const [profileStatus, setProfileStatus] = useState<EmergencyProfileStatus | null>(null);
  const [hasExistingProfile, setHasExistingProfile] = useState<boolean | null>(null);
  const [form, setForm] = useState<ProfileFormState>(() => createEmptyProfileForm());
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<ProfileSaveStatus>("initial");
  const [saveErrorMessage, setSaveErrorMessage] = useState<string | null>(null);

  const baselineRef = useRef<ProfileFormState>(form);
  const isSavingRef = useRef(false);

  const load = useCallback(async () => {
    setLoadErrorMessage(null);
    setIsLoadingProfile(true);
    setIsLoadingStatus(true);

    try {
      const [loadedProfile, loadedStatus] = await Promise.all([
        getEmergencyProfile(),
        getEmergencyProfileStatus(),
      ]);

      const nextForm = loadedProfile ? createProfileForm(loadedProfile) : createEmptyProfileForm();

      setProfile(loadedProfile);
      setHasExistingProfile(loadedProfile !== null);
      setProfileStatus(loadedStatus);
      setForm(nextForm);
      baselineRef.current = nextForm;
      setSaveStatus("initial");
      setSaveErrorMessage(null);
    } catch (error) {
      setLoadErrorMessage(getProfileErrorMessage(error, "No se pudo cargar el perfil de emergencia."));
    } finally {
      setIsLoadingProfile(false);
      setIsLoadingStatus(false);
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const applyFormUpdate = useCallback((updater: (current: ProfileFormState) => ProfileFormState) => {
    setForm((current) => {
      const next = updater(current);
      setSaveStatus((currentStatus) => {
        const stillEqualToBaseline = areFormsEqual(next, baselineRef.current);

        if (currentStatus === "saving") {
          return currentStatus;
        }

        return stillEqualToBaseline ? "initial" : "dirty";
      });
      return next;
    });
  }, []);

  const updateTextField = useCallback(
    (name: ProfileTextFieldName, value: string) => {
      applyFormUpdate((current) => ({ ...current, [name]: value }));
    },
    [applyFormUpdate],
  );

  const updateDecisionField = useCallback(
    (name: ProfileDecisionFieldName, checked: boolean) => {
      applyFormUpdate((current) => {
        const next = { ...current, [name]: checked };

        if (checked && name === "medical_conditions_none") {
          next.medical_conditions = "";
        }

        if (checked && name === "allergies_none") {
          next.allergies = "";
        }

        if (checked && name === "medications_none") {
          next.medications = "";
        }

        return next;
      });
    },
    [applyFormUpdate],
  );

  const updateConsent = useCallback(
    (checked: boolean) => {
      applyFormUpdate((current) => ({
        ...current,
        is_public: checked ? current.is_public : false,
        public_consent_accepted_at: checked ? new Date().toISOString() : null,
        public_consent_version: checked
          ? profileStatus?.publication_eligibility.consent_version ?? current.public_consent_version
          : null,
      }));
    },
    [applyFormUpdate, profileStatus],
  );

  const updateIsPublic = useCallback(
    (checked: boolean) => {
      applyFormUpdate((current) => ({ ...current, is_public: checked }));
    },
    [applyFormUpdate],
  );

  const isDirty = saveStatus === "dirty";

  const save = useCallback(async () => {
    if (!emailVerified || isSavingRef.current) {
      return;
    }

    isSavingRef.current = true;
    setSaveStatus("saving");
    setSaveErrorMessage(null);

    try {
      const savedProfile = await updateEmergencyProfile(createProfilePayload(form));
      const status = await getEmergencyProfileStatus();
      const nextForm = createProfileForm(savedProfile);

      setProfile(savedProfile);
      setForm(nextForm);
      baselineRef.current = nextForm;
      setProfileStatus(status);
      setHasExistingProfile(true);
      setSaveStatus("saved");
    } catch (error) {
      setSaveStatus("error");
      setSaveErrorMessage(getProfileErrorMessage(error, "No se pudo guardar el perfil de emergencia."));
    } finally {
      isSavingRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [emailVerified, form]);

  useEffect(() => {
    function handleBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }

    if (!isDirty) {
      return undefined;
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  return {
    profile,
    profileStatus,
    hasExistingProfile,
    form,
    isLoadingProfile,
    isLoadingStatus,
    loadErrorMessage,
    saveStatus,
    saveErrorMessage,
    isDirty,
    updateTextField,
    updateDecisionField,
    updateConsent,
    updateIsPublic,
    save,
    reload: load,
  };
}
