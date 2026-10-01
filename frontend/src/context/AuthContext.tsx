import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { loadSession, login as apiLogin, logout as apiLogout } from "../services/api";
import type { AuthSession, Role } from "../types";

interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  role: Role | null;
  username: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => loadSession());

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: Boolean(session?.token),
      role: session?.role ?? null,
      username: session?.username ?? null,
      login: async (username, password) => {
        const next = await apiLogin(username, password);
        setSession(next);
      },
      logout: () => {
        apiLogout();
        sessionStorage.removeItem("delta-assessments");
        setSession(null);
      },
    }),
    [session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
