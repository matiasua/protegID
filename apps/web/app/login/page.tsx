"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { getCurrentUser, login } from "@/lib/auth";

function getLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError && error.status === 401) {
    return "Credenciales inválidas.";
  }

  return "No se pudo iniciar sesión. Intenta nuevamente.";
}

function sanitizeReturnTo(value: string | null): string {
  if (!value) {
    return "/dashboard";
  }

  const trimmedValue = value.trim();
  const lowerValue = trimmedValue.toLowerCase();

  if (
    trimmedValue.length === 0 ||
    trimmedValue.length > 300 ||
    !trimmedValue.startsWith("/") ||
    trimmedValue.startsWith("//") ||
    lowerValue.startsWith("http://") ||
    lowerValue.startsWith("https://") ||
    lowerValue.startsWith("/api/") ||
    lowerValue.startsWith("/_next/") ||
    lowerValue === "/login" ||
    lowerValue.startsWith("/login?") ||
    lowerValue === "/register" ||
    lowerValue.startsWith("/register?")
  ) {
    return "/dashboard";
  }

  if (trimmedValue === "/dashboard" || trimmedValue.startsWith("/dashboard?")) {
    return trimmedValue;
  }

  if (/^\/p\/PID-[A-Z0-9]{10}(?:\?.*)?$/.test(trimmedValue)) {
    return trimmedValue;
  }

  return "/dashboard";
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const safeReturnTo = sanitizeReturnTo(searchParams.get("returnTo"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [hasCheckedSession, setHasCheckedSession] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then(() => {
        setIsRedirecting(true);
        router.replace(safeReturnTo);
      })
      .catch(() => undefined)
      .finally(() => setHasCheckedSession(true));
  }, [safeReturnTo, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setErrorMessage(null);

    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      setErrorMessage("Ingresa email y password para iniciar sesión.");
      return;
    }

    setIsLoading(true);

    try {
      await login(trimmedEmail, password);
      setIsRedirecting(true);
      router.replace(safeReturnTo);
    } catch (error) {
      setErrorMessage(getLoginErrorMessage(error));
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

            <p className="mt-8 text-sm font-semibold uppercase tracking-[0.24em] text-sky-700">Acceso seguro</p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Iniciar sesión en ProtegID</h1>
            <p className="mt-4 text-sm leading-6 text-slate-600">
              Accede al dashboard privado. La sesión se administra con una cookie HttpOnly emitida por el backend.
            </p>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              Después de iniciar sesión podrás continuar al dashboard o volver al flujo de activación si venías desde un identificador.
            </div>
          </section>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            {!hasCheckedSession || isRedirecting ? (
              <section className="mb-6 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
                {isRedirecting ? "Redirigiendo..." : "Verificando sesión..."}
              </section>
            ) : null}

            <div className="mb-6">
              <h2 className="text-xl font-semibold tracking-tight">Credenciales</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Ingresa tu email y password para crear una sesión segura.
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
                  disabled={isLoading || isRedirecting}
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
                  disabled={isLoading || isRedirecting}
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

              <Button className="w-full" disabled={isLoading || isRedirecting} type="submit">
                {isRedirecting ? "Redirigiendo..." : isLoading ? "Iniciando sesión..." : "Iniciar sesión"}
              </Button>
            </form>
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
