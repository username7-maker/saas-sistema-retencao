import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";

import { authService, type LoginPayload } from "../services/authService";
import { tokenStorage } from "../services/storage";
import type { User } from "../types";

const SESSION_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

function isAuthFailure(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  const status = error.response?.status;
  return status === 401 || status === 403;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const bootstrap = useCallback(async () => {
    try {
      if (!tokenStorage.getAccessToken()) {
        await authService.restoreSession();
      }
      const currentUser = await authService.me();
      setUser(currentUser);
    } catch (error) {
      if (isAuthFailure(error)) {
        tokenStorage.clear();
      }
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (!user) return;

    const refreshActiveSession = () => {
      // Keep the operator's session warm, but avoid rotating the HttpOnly
      // refresh cookie every few minutes while the access token is still fresh.
      // Fewer rotations reduce race windows across tabs and flaky network edges.
      void authService.ensureSession({ clearOnFailure: false }).catch(() => undefined);
    };

    const intervalId = window.setInterval(refreshActiveSession, SESSION_REFRESH_INTERVAL_MS);
    window.addEventListener("focus", refreshActiveSession);
    window.addEventListener("online", refreshActiveSession);
    window.addEventListener("pageshow", refreshActiveSession);
    document.addEventListener("visibilitychange", refreshActiveSession);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", refreshActiveSession);
      window.removeEventListener("online", refreshActiveSession);
      window.removeEventListener("pageshow", refreshActiveSession);
      document.removeEventListener("visibilitychange", refreshActiveSession);
    };
  }, [user]);

  const login = useCallback(async (payload: LoginPayload) => {
    await authService.login(payload);
    const currentUser = await authService.me();
    setUser(currentUser);
    return currentUser;
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      if (!tokenStorage.getAccessToken()) {
        await authService.restoreSession();
      }
      const currentUser = await authService.me();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      if (isAuthFailure(error)) {
        tokenStorage.clear();
        setUser(null);
        return null;
      }
      if (user) {
        return user;
      }
      return null;
    }
  }, [user]);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      logout,
      refreshUser,
    }),
    [user, loading, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
