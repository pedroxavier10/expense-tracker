"use client";

/**
 * Minimal auth state. Reads the token from localStorage on mount, validates it
 * by calling /auth/me, and exposes Google/dev login and logout helpers.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useLocale } from "@/components/LocaleProvider";
import * as api from "@/lib/api";
import { isLocale } from "@/lib/i18n";
import type { User } from "@/types/api";

interface AuthState {
  user: User | null;
  loading: boolean;
  loginWithGoogle: (credential: string) => Promise<void>;
  devLogin: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const { setLocale } = useLocale();

  const adoptUser = useCallback(
    (me: User) => {
      setUser(me);
      // Mirror the backend-preferred language locally without re-PATCHing.
      if (me.language && isLocale(me.language)) {
        setLocale(me.language, { persist: false });
      }
    },
    [setLocale],
  );

  useEffect(() => {
    const token = api.getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .getMe()
      .then(adoptUser)
      .catch(() => api.clearToken())
      .finally(() => setLoading(false));
  }, [adoptUser]);

  const loginWithGoogle = useCallback(
    async (credential: string) => {
      await api.loginWithGoogle(credential);
      adoptUser(await api.getMe());
    },
    [adoptUser],
  );

  const devLogin = useCallback(async () => {
    await api.devLogin();
    adoptUser(await api.getMe());
  }, [adoptUser]);

  const logout = useCallback(() => {
    api.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, devLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
