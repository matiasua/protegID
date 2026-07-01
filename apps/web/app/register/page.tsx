"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { register } from "@/lib/auth";

function getRegisterErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }

  return "No se pudo crear la cuenta.";
}

function getSafeReturnTo(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const trimmedValue = value.trim();
  const lowerValue = trimmedValue.toLowerCase();

  if (
    !trimmedValue.startsWith("/") ||
    trimmedValue.startsWith("//") ||
    lowerValue.startsWith("http://") ||
    lowerValue.startsWith("https://")
  ) {
    return null;
  }

  return trimmedValue;
}

function RegisterContent() {
  const searchParams = useSearchParams();
  const returnTo = getSafeReturnTo(searchParams.get("returnTo"));
  const loginHref = returnTo ? `/login?returnTo=${encodeURIComponent(returnTo)}` : "/login";

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreated, setIsCreated] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setErrorMessage(null);
    setIsCreated(false);
    setRegisteredEmail(null);

    const trimmedFullName = fullName.trim();
    const trimmedEmail = email.trim();

    if (!trimmedFullName) {
      setErrorMessage("Ingresa tu nombre para crear la cuenta.");
      return;
    }

    if (!trimmedEmail) {
      setErrorMessage("Ingresa tu email para crear la cuenta.");
      return;
    }

    if (!password) {
      setErrorMessage("Ingresa un password para crear la cuenta.");
      return;
    }

    if (password.length < 8) {
      setErrorMessage("El password debe tener al menos 8 caracteres.");
      return;
    }

    setIsLoading(true);

    try {
      const response = await register({
        email: trimmedEmail,
        password,
        full_name: trimmedFullName,
      });
      setPassword("");
      setRegisteredEmail(response.user.email);
      setIsCreated(true);
    } catch (error) {
      setErrorMessage(getRegisterErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.18),_transparent_30rem)] px-4 py-8 text-slate-950 sm:px-6 lg:py-12">
      <section className="mx-auto flex min-h-[calc(100vh-6rem)] max-w-5xl items-center justify-center">
        <div className="grid w-full gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <Link className="inline-flex text-sm font-medium text-sky-700 underline-offset-4 hover:underline" href="/">
              Volver al inicio
            </Link>

            <p className="mt-8 text-sm font-semibold uppercase tracking-[0.24em] text-sky-700">Registro ProtegID</p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Crear cuenta</h1>
            <p className="mt-4 text-sm leading-6 text-slate-600">
              Crea una cuenta para activar tu identificador físico y luego completar tu perfil de emergencia desde el
              dashboard.
            </p>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              El registro no inicia sesión automáticamente. Después de crear la cuenta, inicia sesión para continuar con
              la activación.
            </div>
          </section>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <div className="mb-6">
              <h2 className="text-xl font-semibold tracking-tight">Datos de cuenta</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Usa un email al que tengas acceso y un password de al menos 8 caracteres.
              </p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-900" htmlFor="full-name">
                  Nombre
                </label>
                <input
                  autoComplete="name"
                  className="h-11 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isLoading}
                  id="full-name"
                  name="full_name"
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Nombre Usuario"
                  type="text"
                  value={fullName}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-900" htmlFor="email">
                  Email
                </label>
                <input
                  autoComplete="email"
                  className="h-11 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isLoading}
                  id="email"
                  name="email"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="tu@email.com"
                  type="email"
                  value={email}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-900" htmlFor="password">
                  Password
                </label>
                <input
                  autoComplete="new-password"
                  className="h-11 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isLoading}
                  id="password"
                  name="password"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  type="password"
                  value={password}
                />
              </div>

              {errorMessage ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800" role="alert">
                  {errorMessage}
                </div>
              ) : null}

              <Button className="w-full" disabled={isLoading} type="submit">
                {isLoading ? "Creando cuenta..." : "Crear cuenta"}
              </Button>
            </form>

            {isCreated ? (
              <section className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                <p className="font-semibold">Cuenta creada. Te enviamos un correo de verificación.</p>
                {registeredEmail ? <p className="mt-2 break-words font-medium">Correo registrado: {registeredEmail}</p> : null}
                <p className="mt-2 leading-6">Revisa tu bandeja de entrada antes de activar identificadores o publicar tu ProtegID.</p>
                <Button asChild className="mt-4 w-full sm:w-auto">
                  <Link href={loginHref}>Ir a iniciar sesión</Link>
                </Button>
              </section>
            ) : null}

            <div className="mt-6 flex flex-col gap-3 text-sm sm:flex-row sm:items-center sm:justify-between">
              <Link className="font-medium text-sky-700 underline-offset-4 hover:underline" href={loginHref}>
                Ya tengo cuenta
              </Link>
              {returnTo ? (
                <Link className="font-medium text-slate-600 underline-offset-4 hover:underline" href={returnTo}>
                  Volver al identificador
                </Link>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <RegisterContent />
    </Suspense>
  );
}
