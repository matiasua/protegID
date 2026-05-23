"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { login } from "@/lib/auth";
import { setSessionToken } from "@/lib/session";
import type { LoginResponse } from "@/types/auth";

function getLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError && error.status === 401) {
    return "Credenciales inválidas.";
  }

  return "No se pudo iniciar sesión. Intenta nuevamente.";
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginResponse, setLoginResponse] = useState<LoginResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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
    } catch (error) {
      setErrorMessage(getLoginErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(14,165,233,0.18),_transparent_30rem)] px-6 py-10">
      <section className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl items-center justify-center">
        <div className="w-full max-w-xl rounded-3xl border bg-card/95 p-6 shadow-sm backdrop-blur md:p-10">
          <Link className="mb-6 inline-flex text-sm font-medium text-sky-700 underline-offset-4 hover:underline" href="/">
            Volver al inicio
          </Link>

          <div className="mb-8">
            <p className="mb-3 text-sm font-medium uppercase tracking-[0.24em] text-sky-600">
              Auth temporal
            </p>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
              Iniciar sesión en ProtegID
            </h1>
            <p className="mt-4 text-sm leading-6 text-muted-foreground">
              Esta es una base temporal de login. Si el inicio de sesión es correcto, copia el token y pégalo en {" "}
              <Link className="font-medium text-sky-700 underline underline-offset-4" href="/dashboard">
                /dashboard
              </Link>
              .
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-900" htmlFor="email">
                Email
              </label>
              <input
                autoComplete="email"
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
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
                className="h-11 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
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
              <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
                {errorMessage}
              </div>
            ) : null}

            <Button className="w-full" disabled={isLoading} type="submit">
              {isLoading ? "Iniciando sesión..." : "Iniciar sesión"}
            </Button>
          </form>

          {loginResponse ? (
            <section className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <p className="font-medium">Inicio de sesión correcto.</p>
              <p className="mt-2">
                Token type: <span className="font-mono">{loginResponse.token_type}</span>
              </p>
              <label className="mt-4 block font-medium" htmlFor="access-token">
                Access token temporal
              </label>
              <textarea
                className="mt-2 min-h-32 w-full resize-y rounded-md border border-emerald-200 bg-white p-3 font-mono text-xs text-slate-900 shadow-sm outline-none focus-visible:ring-1 focus-visible:ring-emerald-500"
                id="access-token"
                readOnly
                value={loginResponse.access_token}
              />
              <p className="mt-2 text-emerald-800">
                Copia este token y pégalo manualmente en /dashboard. También se guarda solo en sessionStorage durante la sesión del navegador.
              </p>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}
