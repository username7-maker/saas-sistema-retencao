const apiBaseEnv = import.meta.env.VITE_API_BASE_URL?.trim();
const wsBaseEnv = (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim();

function resolveApiBaseUrl(): string {
  if (import.meta.env.PROD && !apiBaseEnv) {
    throw new Error("VITE_API_BASE_URL ausente na build de producao");
  }

  return apiBaseEnv || "http://127.0.0.1:8000";
}

function resolveWsBaseUrl(apiBaseUrl: string): string {
  return wsBaseEnv || apiBaseUrl.replace(/^http/, "ws");
}

export const API_BASE_URL = resolveApiBaseUrl();
export const WS_BASE_URL = resolveWsBaseUrl(API_BASE_URL);
