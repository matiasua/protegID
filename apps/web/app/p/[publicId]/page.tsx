import { notFound } from "next/navigation";

import { getPublicProfile } from "@/lib/public-profile";
import type { PublicProfile } from "@/types/public-profile";

type PublicProfilePageProps = {
  params: Promise<{
    publicId: string;
  }>;
};

type ProfileField = {
  label: string;
  value: string | null;
};

function formatValue(value: string | null) {
  return value && value.trim().length > 0 ? value : "No informado";
}

export default async function PublicProfilePage({ params }: PublicProfilePageProps) {
  const { publicId } = await params;
  const profile = await getPublicProfile(publicId);

  if (profile === null) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto max-w-3xl rounded-2xl border bg-white p-6 shadow-sm md:p-8">
        <p className="text-sm font-medium uppercase tracking-wide text-sky-700">ProtegID</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Perfil publico de emergencia</h1>
        <ProfileDetails profile={profile} />
      </section>
    </main>
  );
}

function ProfileDetails({ profile }: { profile: PublicProfile }) {
  const fields: ProfileField[] = [
    { label: "Nombre", value: profile.display_name },
    { label: "Tipo de sangre", value: profile.blood_type },
    { label: "Alergias", value: profile.allergies },
    { label: "Condiciones medicas", value: profile.medical_conditions },
    { label: "Medicamentos", value: profile.medications },
    { label: "Contacto de emergencia", value: profile.emergency_contact_name },
    { label: "Telefono de emergencia", value: profile.emergency_contact_phone },
    { label: "Relacion del contacto", value: profile.emergency_contact_relationship },
    { label: "Notas", value: profile.notes },
  ];

  return (
    <dl className="mt-8 divide-y rounded-xl border">
      {fields.map((field) => (
        <div className="grid gap-1 px-4 py-4 md:grid-cols-3 md:gap-6" key={field.label}>
          <dt className="text-sm font-medium text-muted-foreground">{field.label}</dt>
          <dd className="md:col-span-2">{formatValue(field.value)}</dd>
        </div>
      ))}
    </dl>
  );
}
