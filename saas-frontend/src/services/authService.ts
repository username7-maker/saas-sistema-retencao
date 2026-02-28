import { api } from "./api";
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
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    return data;
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
