import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ErrorBoundary, isRecoverableChunkLoadError } from "../components/common/ErrorBoundary";

function Boom(): never {
  throw new Error("Test error");
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("renders children normally when there is no error", () => {
    render(
      <ErrorBoundary>
        <div>OK</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("renders fallback UI when a child throws", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/algo deu errado/i)).toBeInTheDocument();
    consoleSpy.mockRestore();
  });

  it("renders custom fallback when provided", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary fallback={<p>Custom fallback</p>}>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Custom fallback")).toBeInTheDocument();
    consoleSpy.mockRestore();
  });

  it("preserves the automatic chunk reload guard across the post-reload mount", () => {
    window.sessionStorage.setItem("ai_gym_chunk_reload_attempted", String(Date.now()));

    render(
      <ErrorBoundary>
        <div>Reloaded application shell</div>
      </ErrorBoundary>,
    );

    expect(window.sessionStorage.getItem("ai_gym_chunk_reload_attempted")).not.toBeNull();
  });
});

describe("isRecoverableChunkLoadError", () => {
  it("recognizes Vite dynamic import failures after a deployment", () => {
    expect(isRecoverableChunkLoadError(new TypeError("Failed to fetch dynamically imported module"))).toBe(true);
  });

  it("recognizes webpack-style chunk failures", () => {
    expect(isRecoverableChunkLoadError(new Error("Loading chunk 123 failed"))).toBe(true);
  });

  it("does not treat ordinary render errors as reload-safe", () => {
    expect(isRecoverableChunkLoadError(new Error("Cannot read properties of undefined"))).toBe(false);
  });
});
