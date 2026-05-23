"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";
import type { AuthUser } from "@/types/auth";

function getValidationErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError && (error.status === 401 || error.status === 403)) {
    return "Token invalido, expirado o sin permisos para acceder al panel.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No se pudo validar la sesion.";
}

export default function DashboardPage() {
  const [accessToken, setAccessToken] = useState("");
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  async function handleValidateSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = accessToken.trim();
    setErrorMessage(null);
    setCurrentUser(null);

    if (!token) {
      setErrorMessage("Pega un access token antes de validar la sesion.");
      return;
    }

    setIsValidating(true);

    try {
      const user = await getCurrentUser(token);
      setCurrentUser(user);
    } catch (error) {
      setErrorMessage(getValidationErrorMessage(error));
    } finally {
      setIsValidating(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8 text-slate-950 sm:px-6 lg:py-12">
      <section className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">Area privada</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Panel privado ProtegID</h1>
          <p className="mt-4 text-base leading-7 text-slate-600">
            Esta pantalla es una validacion temporal por token para preparar el dashboard privado. Por ahora pega manualmente un access token JWT y se validara contra la API.
          </p>

          <form className="mt-8 space-y-4" onSubmit={handleValidateSession}>
            <div>
              <label className="text-sm font-medium text-slate-700" htmlFor="access-token">
                Access token
              </label>
              <textarea
                className="mt-2 min-h-36 w-full resize-y rounded-2xl border border-slate-300 bg-white px-4 py-3 font-mono text-sm text-slate-950 shadow-sm outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
                id="access-token"
                onChange={(event) => setAccessToken(event.target.value)}
                placeholder="Pega aqui el access token temporal"
                value={accessToken}
              />
              <p className="mt-2 text-sm text-slate-500">
                El token se conserva solo en el estado de esta pagina. No se guarda en localStorage ni cookies.
              </p>
            </div>

            <Button disabled={isValidating} type="submit">
              {isValidating ? "Validando..." : "Validar sesión"}
            </Button>
          </form>
        </div>

        <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-xl font-semibold tracking-tight">Estado de sesion</h2>

          {isValidating ? (
            <p className="mt-4 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              Validando token contra la API...
            </p>
          ) : null}

          {errorMessage ? (
            <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
              {errorMessage}
            </p>
          ) : null}

          {currentUser ? (
            <dl className="mt-5 divide-y divide-slate-100 rounded-2xl border border-slate-200">
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Nombre</dt>
                <dd className="text-sm text-slate-950 sm:col-span-2">{currentUser.full_name ?? "Sin nombre informado"}</dd>
              </div>
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Email</dt>
                <dd className="break-words text-sm text-slate-950 sm:col-span-2">{currentUser.email}</dd>
              </div>
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Role</dt>
                <dd className="text-sm text-slate-950 sm:col-span-2">{currentUser.role}</dd>
              </div>
              <div className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-medium text-slate-500">Status</dt>
                <dd className="text-sm text-slate-950 sm:col-span-2">{currentUser.status}</dd>
              </div>
            </dl>
          ) : null}

          {!isValidating && !errorMessage && !currentUser ? (
            <p className="mt-4 text-sm leading-6 text-slate-600">
              Aun no hay una sesion validada. Pega un token y presiona "Validar sesión".
            </p>
          ) : null}
        </aside>
      </section>
    </main>
  );
}
