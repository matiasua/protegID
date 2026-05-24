import { ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

const FLOW_STEPS = [
  "Activa tu identificador.",
  "Completa tu perfil de emergencia.",
  "Comparte acceso público mediante QR/NFC.",
];

const MVP_STATUS_ITEMS = [
  "Login temporal.",
  "Dashboard privado.",
  "Perfil público por public_id.",
  "QR generado hacia /p/{public_id}.",
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.18),_transparent_30rem)] px-4 py-8 text-slate-950 sm:px-6 lg:py-12">
      <section className="mx-auto grid min-h-[calc(100vh-6rem)] max-w-5xl gap-6 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 lg:p-10">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-sky-100 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-800">
            <ShieldCheck className="h-4 w-4" />
            MVP de emergencia
          </div>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            ProtegID
          </h1>

          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
            Identificadores físicos de emergencia con QR y NFC.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild>
              <Link href="/login">Iniciar sesión</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/dashboard">Ir al dashboard</Link>
            </Button>
          </div>

          <p className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
            Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.
          </p>
        </div>

        <div className="grid gap-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Flujo principal</p>
            <h2 className="mt-3 text-2xl font-bold tracking-tight">Del identificador al perfil público</h2>
            <ol className="mt-6 space-y-4">
              {FLOW_STEPS.map((step, index) => (
                <li className="flex gap-4" key={step}>
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sm font-bold text-sky-800">
                    {index + 1}
                  </span>
                  <span className="pt-1 text-sm leading-6 text-slate-700">{step}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-sky-700">Estado actual MVP</p>
            <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              {MVP_STATUS_ITEMS.map((item) => (
                <li className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700" key={item}>
                  {item}
                </li>
              ))}
            </ul>
          </section>
        </div>
      </section>
    </main>
  );
}
