const apiBaseEnv = import.meta.env.VITE_API_BASE_URL?.trim();
const wsBaseEnv = (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim();
const SAME_ORIGIN_API_BASE_URL = "same-origin";
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "::1"]);

function resolveApiBaseUrl(): string {
  const browserOrigin = typeof window !== "undefined" ? window.location.origin : "";
  const browserHostname = typeof window !== "undefined" ? window.location.hostname : "";
  const isHostedBrowserBuild = Boolean(browserOrigin && !LOCAL_HOSTNAMES.has(browserHostname));

  if (apiBaseEnv === SAME_ORIGIN_API_BASE_URL || (import.meta.env.PROD && isHostedBrowserBuild)) {
    return browserOrigin;
  }

  if (import.meta.env.PROD && !apiBaseEnv && browserOrigin) {
    return window.location.origin;
  }

  if (import.meta.env.PROD && !apiBaseEnv) {
    throw new Error("VITE_API_BASE_URL ausente na build de producao");
  }

  return apiBaseEnv || "http://127.0.0.1:8000";
}

function resolveWsBaseUrl(apiBaseUrl: string): string {
  if (wsBaseEnv) return wsBaseEnv;
  if (import.meta.env.PROD && apiBaseEnv && apiBaseEnv !== SAME_ORIGIN_API_BASE_URL) {
    return apiBaseEnv.replace(/^http/, "ws");
  }
  return apiBaseUrl.replace(/^http/, "ws");
}

export const API_BASE_URL = resolveApiBaseUrl();
export const WS_BASE_URL = resolveWsBaseUrl(API_BASE_URL);
