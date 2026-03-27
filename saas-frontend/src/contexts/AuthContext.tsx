import { createContext, useCallback, useEffect, useMemo, useState } from "react";

import { authService, type LoginPayload } from "../services/authService";
import { tokenStorage } from "../services/storage";
import type { User } from "../types";

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
    } catch {
      tokenStorage.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

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
    } catch {
      tokenStorage.clear();
      setUser(null);
      return null;
    }
  }, []);

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
