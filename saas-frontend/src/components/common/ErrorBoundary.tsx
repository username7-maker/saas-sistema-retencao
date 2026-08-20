import { Component, ErrorInfo, ReactNode } from "react";

const CHUNK_RELOAD_FLAG = "ai_gym_chunk_reload_attempted";
const CHUNK_RELOAD_GUARD_MS = 60_000;

export function isRecoverableChunkLoadError(error: unknown): boolean {
  const value = error instanceof Error ? `${error.name} ${error.message}` : String(error ?? "");
  return /ChunkLoadError|Loading chunk|Failed to fetch dynamically imported module|Importing a module script failed/i.test(value);
}

function getChunkReloadStorage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function hasAlreadyTriedChunkReload(): boolean {
  const storage = getChunkReloadStorage();
  const rawAttemptedAt = storage?.getItem(CHUNK_RELOAD_FLAG);
  if (!storage || !rawAttemptedAt) return false;

  const attemptedAt = Number(rawAttemptedAt);
  if (Number.isFinite(attemptedAt) && attemptedAt > 1 && Date.now() - attemptedAt <= CHUNK_RELOAD_GUARD_MS) {
    return true;
  }

  storage.removeItem(CHUNK_RELOAD_FLAG);
  return false;
}

function markChunkReloadAttempted(): void {
  getChunkReloadStorage()?.setItem(CHUNK_RELOAD_FLAG, String(Date.now()));
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary]", error, info.componentStack);
    if (isRecoverableChunkLoadError(error) && getChunkReloadStorage() && !hasAlreadyTriedChunkReload()) {
      markChunkReloadAttempted();
      window.location.reload();
      return;
    }
  }

  private handleRetry = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "60vh",
            gap: "1rem",
            padding: "2rem",
            textAlign: "center",
          }}
        >
          <h2 style={{ fontSize: "1.5rem", fontWeight: 600 }}>Algo deu errado</h2>
          <p style={{ color: "var(--lovable-muted, #6b7280)", maxWidth: "480px" }}>
            Ocorreu um erro inesperado nesta pagina. Tente recarregar ou entre em contato com o suporte.
          </p>
          <button
            onClick={this.handleRetry}
            style={{
              padding: "0.5rem 1.5rem",
              borderRadius: "0.375rem",
              background: "var(--lovable-brand, #6fa7c7)",
              color: "#fff",
              border: "none",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            Tentar novamente
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
