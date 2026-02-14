import { createContext, useCallback, useEffect, useMemo, useState } from "react";

import { authService, type LoginPayload } from "../services/authService";
import { tokenStorage } from "../services/storage";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const bootstrap = useCallback(async () => {
    const token = tokenStorage.getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
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
    }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
