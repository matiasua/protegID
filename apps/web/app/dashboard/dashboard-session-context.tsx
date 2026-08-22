"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { getCurrentUser } from "@/lib/auth";
import type { AuthUser } from "@/types/auth";

type DashboardSessionContextValue = {
  user: AuthUser | null;
  hasCheckedSession: boolean;
  isValidating: boolean;
  refresh: () => Promise<void>;
  clear: () => void;
};

const DashboardSessionContext = createContext<DashboardSessionContextValue | null>(null);

export function DashboardSessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [hasCheckedSession, setHasCheckedSession] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  const refresh = useCallback(async () => {
    setIsValidating(true);

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setIsValidating(false);
      setHasCheckedSession(true);
    }
  }, []);

  const clear = useCallback(() => {
    setUser(null);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <DashboardSessionContext.Provider value={{ user, hasCheckedSession, isValidating, refresh, clear }}>
      {children}
    </DashboardSessionContext.Provider>
  );
}

export function useDashboardSession(): DashboardSessionContextValue {
  const context = useContext(DashboardSessionContext);

  if (!context) {
    throw new Error("useDashboardSession debe usarse dentro de DashboardSessionProvider.");
  }

  return context;
}
