import axios, { AxiosError, AxiosRequestConfig } from "axios";

import { tokenStorage } from "./storage";
import { API_BASE_URL } from "./runtimeConfig";
import type { TokenPair } from "../types";

interface RetriableRequestConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  withCredentials: true,
});

let refreshInFlight: Promise<string> | null = null;

export async function requestAccessTokenRefresh(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = axios
      .post<TokenPair>(`${API_BASE_URL}/api/v1/auth/refresh`, undefined, {
        timeout: 20000,
        withCredentials: true,
      })
      .then(({ data }) => {
        tokenStorage.setAccessToken(data.access_token);
        return data.access_token;
      })
      .catch((error) => {
        tokenStorage.clear();
        throw error;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }

  return refreshInFlight;
}

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableRequestConfig;
    const requestUrl = originalRequest?.url ?? "";
    if (
      error.response?.status !== 401 ||
      originalRequest?._retry ||
      requestUrl.includes("/api/v1/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    try {
      const accessToken = await requestAccessTokenRefresh();
      originalRequest.headers = originalRequest.headers ?? {};
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return api(originalRequest);
    } catch {
      tokenStorage.clear();
      return Promise.reject(error);
    }
  },
);
