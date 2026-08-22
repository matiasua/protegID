"use client";

import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/dashboard/page-header";
import { useDashboardSession } from "@/app/dashboard/dashboard-session-context";
import { EmergencyContactSection } from "@/components/dashboard/profile/emergency-contact-section";
import { EmergencyProfilePreview } from "@/components/dashboard/profile/emergency-profile-preview";
import { MedicalInformationSection } from "@/components/dashboard/profile/medical-information-section";
import { PersonalInformationSection } from "@/components/dashboard/profile/personal-information-section";
import { ProfileSaveBar } from "@/components/dashboard/profile/profile-save-bar";
import { ProfileStatusCard } from "@/components/dashboard/profile/profile-status-card";
import { PublicationSection } from "@/components/dashboard/profile/publication-section";
import { EMAIL_VERIFICATION_REQUIRED_MESSAGE } from "@/components/dashboard/profile/types";
import { useEmergencyProfileForm } from "@/components/dashboard/profile/use-emergency-profile-form";
import type { AuthUser } from "@/types/auth";

function isEmailVerified(user: AuthUser | null): boolean {
  return user?.email_verified_at !== null && user?.email_verified_at !== undefined;
}

export default function PerfilPage() {
  const { user: currentUser } = useDashboardSession();
  const emailVerified = isEmailVerified(currentUser);

  const {
    profile,
    profileStatus,
    hasExistingProfile,
    form,
    isLoadingProfile,
    isLoadingStatus,
    loadErrorMessage,
    saveStatus,
    saveErrorMessage,
    updateTextField,
    updateDecisionField,
    updateConsent,
    updateIsPublic,
    save,
  } = useEmergencyProfileForm(Boolean(currentUser), emailVerified);

  const fieldsDisabled = isLoadingProfile || saveStatus === "saving" || !emailVerified;

  return (
    <>
      <PageHeader
        description="Gestiona los datos médicos y de contacto que se muestran en tus identificadores ProtegID."
        title="Perfil de emergencia"
      />

      {currentUser && !emailVerified ? (
        <p className="rounded-lg border border-warning/30 bg-warning-muted px-4 py-3 text-sm font-medium text-warning">
          {EMAIL_VERIFICATION_REQUIRED_MESSAGE}
        </p>
      ) : null}

      {isLoadingProfile ? (
        <p className="rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 text-sm text-primary">
          Cargando perfil de emergencia...
        </p>
      ) : null}

      {loadErrorMessage ? (
        <Card surface="danger">
          <CardContent className="pt-4 text-sm font-medium text-danger sm:pt-5">{loadErrorMessage}</CardContent>
        </Card>
      ) : null}

      {!isLoadingProfile && !loadErrorMessage && hasExistingProfile === false ? (
        <p className="rounded-lg border border-warning/30 bg-warning-muted px-4 py-3 text-sm text-warning">
          Aún no has completado tu perfil de emergencia. Completa los campos obligatorios y guarda para crearlo.
        </p>
      ) : null}

      {!isLoadingProfile && !loadErrorMessage ? (
        <>
          <ProfileStatusCard isLoading={isLoadingStatus} profile={profile} profileStatus={profileStatus} />

          <PersonalInformationSection disabled={fieldsDisabled} form={form} onChangeText={updateTextField} />

          <EmergencyContactSection disabled={fieldsDisabled} form={form} onChangeText={updateTextField} />

          <MedicalInformationSection
            disabled={fieldsDisabled}
            form={form}
            onChangeDecision={updateDecisionField}
            onChangeText={updateTextField}
          />

          <PublicationSection
            disabled={fieldsDisabled}
            form={form}
            onChangeConsent={updateConsent}
            onChangeIsPublic={updateIsPublic}
            profileStatus={profileStatus}
          />

          <EmergencyProfilePreview form={form} />

          <ProfileSaveBar disabled={!emailVerified} errorMessage={saveErrorMessage} onSave={() => void save()} status={saveStatus} />
        </>
      ) : null}
    </>
  );
}
