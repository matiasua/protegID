import { ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.22),_transparent_32rem)] px-6 py-10">
      <section className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl items-center">
        <div className="max-w-2xl rounded-3xl border bg-card/90 p-8 shadow-sm backdrop-blur md:p-12">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border bg-white px-4 py-2 text-sm text-muted-foreground">
            <ShieldCheck className="h-4 w-4 text-sky-500" />
            Setup base del MVP
          </div>

          <h1 className="text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
            ProtegID
          </h1>

          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            Plataforma para identificadores fisicos de emergencia con QR + NFC. Esta version solo contiene la estructura inicial del monorepo y servicios locales.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button disabled>Activacion pendiente</Button>
            <Button variant="outline" disabled>
              Perfil publico pendiente
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
}
