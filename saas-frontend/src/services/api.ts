import axios, { AxiosError, AxiosRequestConfig } from "axios";

import { tokenStorage } from "./storage";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

interface RetriableRequestConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

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
    if (error.response?.status !== 401 || originalRequest?._retry) {
      return Promise.reject(error);
    }

    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) {
      tokenStorage.clear();
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    try {
      const refreshResponse = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const { access_token, refresh_token } = refreshResponse.data;
      tokenStorage.setTokens(access_token, refresh_token);
      originalRequest.headers = originalRequest.headers ?? {};
      originalRequest.headers.Authorization = `Bearer ${access_token}`;
      return api(originalRequest);
    } catch {
      tokenStorage.clear();
      return Promise.reject(error);
    }
  },
);
