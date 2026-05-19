import { AxiosError } from "axios";

interface ApiErrorPayload {
  detail?: string;
  message?: string;
  error?: string;
}

export function isHttpErrorStatus(error: unknown, status: number): boolean {
  return error instanceof AxiosError && error.response?.status === status;
}

export function getHttpErrorDetail(error: unknown, fallbackError: string): string {
  if (error instanceof AxiosError) {
    const payload = error.response?.data as ApiErrorPayload | undefined;
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
    if (typeof payload?.message === "string" && payload.message.trim()) {
      return payload.message;
    }
    if (typeof payload?.error === "string" && payload.error.trim()) {
      return payload.error;
    }
  }
  return fallbackError;
}

export function getPermissionAwareMessage(
  error: unknown,
  fallbackError: string,
  fallbackForbidden = "Voce nao tem permissao para acessar este conteudo.",
): string {
  if (isHttpErrorStatus(error, 403)) {
    return fallbackForbidden;
  }
  return fallbackError;
}
