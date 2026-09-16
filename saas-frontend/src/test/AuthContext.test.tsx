import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuthProvider } from "../contexts/AuthContext";
import { useAuth } from "../hooks/useAuth";

const authServiceMock = vi.hoisted(() => ({
  login: vi.fn(),
  logout: vi.fn(),
  me: vi.fn(),
  restoreSession: vi.fn(),
  ensureSession: vi.fn(),
}));

const tokenStorageMock = vi.hoisted(() => ({
  getAccessToken: vi.fn(),
  clear: vi.fn(),
}));

vi.mock("../services/authService", () => ({
  authService: authServiceMock,
}));

vi.mock("../services/storage", () => ({
  tokenStorage: tokenStorageMock,
}));

function AuthProbe() {
  const { loading, user, login, logout } = useAuth();

  if (loading) {
    return <div>loading</div>;
  }

  return <div>{user ? user.full_name : "anonymous"}<button onClick={() => void login({ email: "b@example.com", password: "x", gym_slug: "gym-b" })}>Login B</button><button onClick={() => void logout().catch(() => undefined)}>Logout</button></div>;
}

function renderAuthProvider(queryClient = new QueryClient()) {
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return queryClient;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    authServiceMock.login.mockReset();
    authServiceMock.logout.mockReset();
    authServiceMock.me.mockReset();
    authServiceMock.restoreSession.mockReset();
    authServiceMock.ensureSession.mockReset();
    tokenStorageMock.getAccessToken.mockReset();
    tokenStorageMock.clear.mockReset();
    window.sessionStorage.clear();
  });

  it("clears assessment drafts on explicit logout even when the request fails", async () => {
    tokenStorageMock.getAccessToken.mockReturnValue("token");
    authServiceMock.me.mockResolvedValue({ id: "user-1", gym_id: "gym-1", full_name: "Owner" });
    authServiceMock.logout.mockRejectedValue(new Error("offline"));
    window.sessionStorage.setItem("cordex:assessment-draft:v2:sample", "draft");
    window.sessionStorage.setItem("unrelated", "keep");
    const queryClient = renderAuthProvider();
    queryClient.setQueryData(["dashboard", "executive"], { gym: "gym-1" });
    await screen.findByText("Owner");
    fireEvent.click(screen.getByText("Logout"));
    await screen.findByText("anonymous");
    expect(window.sessionStorage.getItem("cordex:assessment-draft:v2:sample")).toBeNull();
    expect(window.sessionStorage.getItem("unrelated")).toBe("keep");
    expect(queryClient.getQueryData(["dashboard", "executive"])).toBeUndefined();
  });

  it("clears cached data before exposing a newly authenticated identity", async () => {
    tokenStorageMock.getAccessToken.mockReturnValue(null);
    authServiceMock.restoreSession.mockRejectedValue(new Error("anonymous"));
    authServiceMock.login.mockResolvedValue({ access_token: "token" });
    authServiceMock.me.mockResolvedValueOnce({ id: "user-2", gym_id: "gym-2", full_name: "Owner B" });
    const queryClient = renderAuthProvider();
    queryClient.setQueryData(["dashboard", "executive"], { gym: "gym-1" });
    await screen.findByText("anonymous");
    fireEvent.click(screen.getByText("Login B"));
    await screen.findByText("Owner B");
    expect(queryClient.getQueryData(["dashboard", "executive"])).toBeUndefined();
  });

  it("restores the session from the refresh cookie when no access token is cached", async () => {
    tokenStorageMock.getAccessToken.mockReturnValue(null);
    authServiceMock.restoreSession.mockResolvedValue("new-access-token");
    authServiceMock.me.mockResolvedValue({
      id: "user-1",
      gym_id: "gym-1",
      full_name: "Owner Teste",
      email: "owner@teste.com",
      role: "owner",
      is_active: true,
      created_at: "2026-03-27T00:00:00Z",
    });

    renderAuthProvider();

    await waitFor(() => {
      expect(screen.getByText("Owner Teste")).toBeInTheDocument();
    });

    expect(authServiceMock.restoreSession).toHaveBeenCalledOnce();
    expect(authServiceMock.me).toHaveBeenCalledOnce();
  });

  it("refreshes an active session when the operator returns to the browser tab", async () => {
    tokenStorageMock.getAccessToken.mockReturnValue(null);
    authServiceMock.restoreSession.mockResolvedValue("new-access-token");
    authServiceMock.me.mockResolvedValue({
      id: "user-1",
      gym_id: "gym-1",
      full_name: "Owner Teste",
      email: "owner@example.com",
      role: "owner",
      active: true,
      created_at: "2026-03-27T00:00:00Z",
    });

    const queryClient = new QueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries").mockResolvedValue();
    renderAuthProvider(queryClient);

    await screen.findByText("Owner Teste");
    authServiceMock.restoreSession.mockClear();
    authServiceMock.ensureSession.mockResolvedValue("current-access-token");

    window.dispatchEvent(new Event("focus"));

    await waitFor(() => {
      expect(authServiceMock.ensureSession).toHaveBeenCalledWith({ clearOnFailure: false });
    });
    expect(invalidateQueries).toHaveBeenCalledWith({ refetchType: "active" });
  });

  it("waits until a background tab is visible before recovering it", async () => {
    const visibilitySpy = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    tokenStorageMock.getAccessToken.mockReturnValue("current-access-token");
    authServiceMock.restoreSession.mockResolvedValue("new-access-token");
    authServiceMock.me.mockResolvedValue({
      id: "user-1",
      gym_id: "gym-1",
      full_name: "Owner Teste",
      email: "owner@example.com",
      role: "owner",
      active: true,
      created_at: "2026-03-27T00:00:00Z",
    });

    try {
      renderAuthProvider();

      await screen.findByText("Owner Teste");
      authServiceMock.restoreSession.mockClear();
      authServiceMock.ensureSession.mockResolvedValue("current-access-token");

      document.dispatchEvent(new Event("visibilitychange"));
      expect(authServiceMock.ensureSession).not.toHaveBeenCalled();

      visibilitySpy.mockReturnValue("visible");
      document.dispatchEvent(new Event("visibilitychange"));

      await waitFor(() => {
        expect(authServiceMock.ensureSession).toHaveBeenCalledWith({ clearOnFailure: false });
      });
    } finally {
      visibilitySpy.mockRestore();
    }
  });

  it("does not clear the visible session when a background refresh fails", async () => {
    tokenStorageMock.getAccessToken.mockReturnValue("current-access-token");
    authServiceMock.me.mockResolvedValue({
      id: "user-1",
      gym_id: "gym-1",
      full_name: "Owner Teste",
      email: "owner@example.com",
      role: "owner",
      active: true,
      created_at: "2026-03-27T00:00:00Z",
    });

    renderAuthProvider();

    await screen.findByText("Owner Teste");
    authServiceMock.ensureSession.mockRejectedValue(new Error("refresh failed"));

    window.dispatchEvent(new Event("focus"));

    await waitFor(() => {
      expect(authServiceMock.ensureSession).toHaveBeenCalledWith({ clearOnFailure: false });
    });
    expect(tokenStorageMock.clear).not.toHaveBeenCalled();
    expect(screen.getByText("Owner Teste")).toBeInTheDocument();
  });
});
