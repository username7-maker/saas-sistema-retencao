import axios, { AxiosError, AxiosRequestConfig } from "axios";

import { tokenStorage } from "./storage";
import { API_BASE_URL } from "./runtimeConfig";
import type { TokenPair } from "../types";

interface RetriableRequestConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

interface AccessTokenRefreshOptions {
  clearOnFailure?: boolean;
}

interface RefreshLockRecord {
  ownerId: string;
  expiresAt: number;
}

const REFRESH_LOCK_KEY = "ai_gym_refresh_lock";
const REFRESH_LOCK_TTL_MS = 25_000;
const REFRESH_LOCK_WAIT_MS = 120;
const REFRESH_LOCK_MAX_WAIT_MS = 20_000;
const ACCESS_TOKEN_REFRESH_LEEWAY_MS = 2 * 60 * 1000;
const refreshOwnerId = `tab-${Date.now()}-${Math.random().toString(36).slice(2)}`;

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  withCredentials: true,
});

let refreshInFlight: Promise<string> | null = null;

function getRefreshLockStorage(): Storage | null {
  if (typeof window === "undefined") return null;

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readRefreshLock(storage: Storage): RefreshLockRecord | null {
  try {
    const raw = storage.getItem(REFRESH_LOCK_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<RefreshLockRecord>;
    if (typeof parsed.ownerId !== "string" || typeof parsed.expiresAt !== "number") {
      return null;
    }
    return { ownerId: parsed.ownerId, expiresAt: parsed.expiresAt };
  } catch {
    return null;
  }
}

function writeRefreshLock(storage: Storage): boolean {
  try {
    storage.setItem(
      REFRESH_LOCK_KEY,
      JSON.stringify({
        ownerId: refreshOwnerId,
        expiresAt: Date.now() + REFRESH_LOCK_TTL_MS,
      }),
    );
    return readRefreshLock(storage)?.ownerId === refreshOwnerId;
  } catch {
    return false;
  }
}

function tryAcquireRefreshLock(storage: Storage): boolean {
  const current = readRefreshLock(storage);
  const now = Date.now();
  if (current && current.ownerId !== refreshOwnerId && current.expiresAt > now) {
    return false;
  }
  return writeRefreshLock(storage);
}

function releaseRefreshLock(storage: Storage): void {
  try {
    if (readRefreshLock(storage)?.ownerId === refreshOwnerId) {
      storage.removeItem(REFRESH_LOCK_KEY);
    }
  } catch {
    // Ignore storage failures. The lock is guarded by a short TTL.
  }
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function acquireRefreshLock(): Promise<() => void> {
  const storage = getRefreshLockStorage();
  if (!storage) return () => undefined;

  const startedAt = Date.now();
  while (Date.now() - startedAt < REFRESH_LOCK_MAX_WAIT_MS) {
    if (tryAcquireRefreshLock(storage)) {
      return () => releaseRefreshLock(storage);
    }
    await wait(REFRESH_LOCK_WAIT_MS);
  }

  return () => undefined;
}

function startAccessTokenRefresh(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const releaseLock = await acquireRefreshLock();
      try {
        const { data } = await axios.post<TokenPair>(`${API_BASE_URL}/api/v1/auth/refresh`, undefined, {
          timeout: 20000,
          withCredentials: true,
        });
        tokenStorage.setAccessToken(data.access_token);
        return data.access_token;
      } finally {
        releaseLock();
      }
    })()
      .finally(() => {
        refreshInFlight = null;
      });
  }

  return refreshInFlight;
}

export async function requestAccessTokenRefresh(options: AccessTokenRefreshOptions = {}): Promise<string> {
  try {
    return await startAccessTokenRefresh();
  } catch (error) {
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    const isAuthFailure = status === 401 || status === 403;
    if (options.clearOnFailure !== false && isAuthFailure) {
      tokenStorage.clear();
    }
    throw error;
  }
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return window.atob(padded);
}

function getAccessTokenExpiresAtMs(accessToken: string | null): number | null {
  if (!accessToken) return null;
  const payloadSegment = accessToken.split(".")[1];
  if (!payloadSegment) return null;

  try {
    const payload = JSON.parse(decodeBase64Url(payloadSegment)) as { exp?: unknown };
    const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp);
    return Number.isFinite(exp) ? exp * 1000 : null;
  } catch {
    return null;
  }
}

export function isAccessTokenExpiringSoon(accessToken: string | null, nowMs = Date.now()): boolean {
  const expiresAtMs = getAccessTokenExpiresAtMs(accessToken);
  if (!expiresAtMs) return true;
  return expiresAtMs - nowMs <= ACCESS_TOKEN_REFRESH_LEEWAY_MS;
}

function isAuthEndpointRequest(requestUrl: string): boolean {
  return requestUrl.includes("/api/v1/auth/");
}

api.interceptors.request.use(async (config) => {
  let token = tokenStorage.getAccessToken();
  const requestUrl = config.url ?? "";
  if (token && !isAuthEndpointRequest(requestUrl) && isAccessTokenExpiringSoon(token)) {
    try {
      token = await requestAccessTokenRefresh({ clearOnFailure: false });
    } catch {
      // Keep the current token on transient wake-up failures. If it is really
      // expired, the response interceptor will attempt a normal refresh and
      // clear the session only when the server rejects the refresh token.
    }
  }

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
    } catch (refreshError) {
      const status = axios.isAxiosError(refreshError) ? refreshError.response?.status : undefined;
      if (status === 401 || status === 403) {
        tokenStorage.clear();
      }
      return Promise.reject(error);
    }
  },
);
