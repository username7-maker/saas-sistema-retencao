import { AxiosError } from "axios";

export function isHttpErrorStatus(error: unknown, status: number): boolean {
  return error instanceof AxiosError && error.response?.status === status;
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
