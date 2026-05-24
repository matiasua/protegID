import Link from "next/link";
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

type ProfileSectionProps = {
  title: string;
  description?: string;
  fields: ProfileField[];
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
    <main className="min-h-screen bg-slate-100 px-4 py-6 text-slate-950 sm:px-6 md:py-10">
      <section className="mx-auto max-w-4xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-red-100 bg-red-50 px-5 py-4 sm:px-8">
          <Link className="text-xs font-bold uppercase tracking-[0.22em] text-red-700 underline-offset-4 hover:underline" href="/">
            ProtegID
          </Link>
          <p className="mt-2 text-xs font-bold uppercase tracking-[0.22em] text-red-700">Ficha de emergencia</p>
          <p className="mt-1 text-sm text-red-950">Informacion publica para primeros respondientes.</p>
        </div>

        <ProfileDetails profile={profile} />
      </section>
    </main>
  );
}

function ProfileDetails({ profile }: { profile: PublicProfile }) {
  const medicalFields: ProfileField[] = [
    { label: "Alergias", value: profile.allergies },
    { label: "Condiciones medicas", value: profile.medical_conditions },
  ];

  const contactFields: ProfileField[] = [
    { label: "Contacto de emergencia", value: profile.emergency_contact_name },
    { label: "Telefono de emergencia", value: profile.emergency_contact_phone },
    { label: "Relacion del contacto", value: profile.emergency_contact_relationship },
  ];

  return (
    <div className="space-y-6 p-5 sm:p-8">
      <header className="grid gap-4 md:grid-cols-[1fr_auto] md:items-start">
        <div>
          <p className="text-sm font-medium text-slate-500">Nombre visible</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            {formatValue(profile.display_name)}
          </h1>
        </div>

        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-left md:min-w-44 md:text-center">
          <p className="text-xs font-bold uppercase tracking-wide text-red-700">Tipo de sangre</p>
          <p className="mt-1 text-3xl font-black text-red-800">{formatValue(profile.blood_type)}</p>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        <CriticalCard label="Contacto de emergencia" value={profile.emergency_contact_name} />
        <CriticalCard label="Telefono de emergencia" value={profile.emergency_contact_phone} isPhone />
      </div>

      <ProfileSection
        title="Informacion medica"
        description="Datos importantes para evaluar riesgos inmediatos."
        fields={medicalFields}
      />

      <ProfileSection
        title="Medicamentos"
        fields={[{ label: "Medicamentos actuales", value: profile.medications }]}
      />

      <ProfileSection title="Contacto de emergencia" fields={contactFields} />

      <ProfileSection title="Notas" fields={[{ label: "Notas adicionales", value: profile.notes }]} />
    </div>
  );
}

function CriticalCard({ label, value, isPhone = false }: ProfileField & { isPhone?: boolean }) {
  const formattedValue = formatValue(value);

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      {isPhone && value && value.trim().length > 0 ? (
        <a className="mt-2 block text-2xl font-bold text-sky-700 underline-offset-4 hover:underline" href={`tel:${value}`}>
          {formattedValue}
        </a>
      ) : (
        <p className="mt-2 text-2xl font-bold text-slate-950">{formattedValue}</p>
      )}
    </div>
  );
}

function ProfileSection({ title, description, fields }: ProfileSectionProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-4 py-4 sm:px-5">
        <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>

      <dl className="divide-y divide-slate-100">
      {fields.map((field) => (
        <div className="grid gap-1 px-4 py-4 sm:px-5 md:grid-cols-3 md:gap-6" key={field.label}>
          <dt className="text-sm font-medium text-slate-500">{field.label}</dt>
          <dd className="whitespace-pre-wrap text-base leading-7 text-slate-950 md:col-span-2">
            {formatValue(field.value)}
          </dd>
        </div>
      ))}
      </dl>
    </section>
  );
}
