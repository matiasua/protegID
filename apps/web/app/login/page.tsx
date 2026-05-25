"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { login } from "@/lib/auth";
import { clearSessionToken, getSessionToken, setSessionToken } from "@/lib/session";
import type { LoginResponse } from "@/types/auth";

function getLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError && error.status === 401) {
    return "Credenciales inválidas.";
  }

  return "No se pudo iniciar sesión. Intenta nuevamente.";
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

function LoginContent() {
  const searchParams = useSearchParams();
  const returnTo = getSafeReturnTo(searchParams.get("returnTo"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginResponse, setLoginResponse] = useState<LoginResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [hasTemporarySession, setHasTemporarySession] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setHasTemporarySession(getSessionToken() !== null);
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setErrorMessage(null);
    setLoginResponse(null);

    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      setErrorMessage("Ingresa email y password para iniciar sesión.");
      return;
    }

    setIsLoading(true);

    try {
      const response = await login(trimmedEmail, password);
      setSessionToken(response.access_token);
      setLoginResponse(response);
      setHasTemporarySession(true);
    } catch (error) {
      setErrorMessage(getLoginErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  function handleClearTemporarySession() {
    clearSessionToken();
    setHasTemporarySession(false);
    setLoginResponse(null);
    setErrorMessage(null);
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.18),_transparent_30rem)] px-4 py-8 text-slate-950 sm:px-6 lg:py-12">
      <section className="mx-auto flex min-h-[calc(100vh-6rem)] max-w-5xl items-center justify-center">
        <div className="grid w-full gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <Link className="inline-flex text-sm font-medium text-sky-700 underline-offset-4 hover:underline" href="/">
              Volver al inicio
            </Link>

            <p className="mt-8 text-sm font-semibold uppercase tracking-[0.24em] text-sky-700">Auth temporal</p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Iniciar sesión en ProtegID</h1>
            <p className="mt-4 text-sm leading-6 text-slate-600">
              Accede al dashboard privado del MVP. La sesión se guarda temporalmente en sessionStorage durante la sesión del navegador.
            </p>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              Este login aún es temporal. Después de iniciar sesión podrás continuar manualmente al dashboard sin redirección automática.
            </div>
          </section>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            {hasTemporarySession && !loginResponse ? (
              <section className="mb-6 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
                <p className="font-semibold">Ya existe una sesión temporal activa.</p>
                <p className="mt-2 leading-6">
                  Puedes ir al dashboard o cerrar la sesión temporal antes de iniciar sesión con otras credenciales.
                </p>
                <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                  <Button asChild className="w-full sm:w-auto">
                    <Link href="/dashboard">Ir al dashboard</Link>
                  </Button>
                  <Button className="w-full sm:w-auto" onClick={handleClearTemporarySession} type="button" variant="outline">
                    Cerrar sesión temporal
                  </Button>
                </div>
              </section>
            ) : null}

            <div className="mb-6">
              <h2 className="text-xl font-semibold tracking-tight">Credenciales</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Ingresa tu email y password para crear una sesión temporal del MVP.
              </p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit}>
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
                  autoComplete="current-password"
                  className="h-11 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isLoading}
                  id="password"
                  name="password"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Ingresa tu password"
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
                {isLoading ? "Iniciando sesión..." : "Iniciar sesión"}
              </Button>
            </form>

            {loginResponse ? (
              <section className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="font-semibold">Inicio de sesión correcto.</p>
                    <p className="mt-2">
                      Token type: <span className="font-mono">{loginResponse.token_type}</span>
                    </p>
                  </div>
                  <div className="flex w-full flex-col gap-3 sm:w-auto">
                    {returnTo ? (
                      <Button asChild className="w-full sm:w-auto">
                        <Link href={returnTo}>Continuar activación</Link>
                      </Button>
                    ) : null}
                    <Button asChild className="w-full sm:w-auto">
                      <Link href="/dashboard">Continuar al dashboard</Link>
                    </Button>
                  </div>
                </div>

                <label className="mt-4 block font-medium" htmlFor="access-token">
                  Access token temporal
                </label>
                <textarea
                  className="mt-2 min-h-32 w-full resize-y rounded-2xl border border-emerald-200 bg-white p-3 font-mono text-xs text-slate-900 shadow-sm outline-none focus-visible:ring-1 focus-visible:ring-emerald-500"
                  id="access-token"
                  readOnly
                  value={loginResponse.access_token}
                />
                <p className="mt-2 leading-6 text-emerald-800">
                  El token se guarda en sessionStorage durante la sesión del navegador. Se muestra por transparencia mientras el flujo sigue siendo temporal.
                </p>
              </section>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}
