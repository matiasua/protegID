import Link from "next/link";

export default function PublicProfileNotFound() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-6 text-slate-950 sm:px-6 md:py-10">
      <section className="mx-auto max-w-2xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-red-100 bg-red-50 px-5 py-4 sm:px-8">
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-red-700">ProtegID</p>
          <p className="mt-1 text-sm text-red-950">Ficha de emergencia</p>
        </div>

        <div className="p-6 sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Perfil no disponible</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            No se puede mostrar esta ficha de emergencia
          </h1>
          <p className="mt-4 text-base leading-7 text-slate-600">
            No hay una ficha pública disponible para este identificador.
          </p>
          <Link className="mt-6 inline-flex text-sm font-medium text-sky-700 underline-offset-4 hover:underline" href="/">
            Volver al inicio
          </Link>
        </div>
      </section>
    </main>
  );
}
