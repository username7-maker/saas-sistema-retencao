import { api, requestAccessTokenRefresh } from "./api";
import { tokenStorage } from "./storage";
import type { TokenPair, User } from "../types";

export interface LoginPayload {
  email: string;
  password: string;
  gym_slug: string;
}

export const authService = {
  async login(payload: LoginPayload): Promise<TokenPair> {
    const { data } = await api.post<TokenPair>("/api/v1/auth/login", payload);
    tokenStorage.setAccessToken(data.access_token);
    return data;
  },

  async restoreSession(): Promise<string> {
    return requestAccessTokenRefresh();
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>("/api/v1/users/me");
    return data;
  },

  async logout(): Promise<void> {
    try {
      await api.post("/api/v1/auth/logout");
    } finally {
      tokenStorage.clear();
    }
  },
};
