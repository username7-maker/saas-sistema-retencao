import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuthProvider } from "../contexts/AuthContext";
import { useAuth } from "../hooks/useAuth";

const authServiceMock = vi.hoisted(() => ({
  login: vi.fn(),
  logout: vi.fn(),
  me: vi.fn(),
  restoreSession: vi.fn(),
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
  const { loading, user } = useAuth();

  if (loading) {
    return <div>loading</div>;
  }

  return <div>{user ? user.full_name : "anonymous"}</div>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    authServiceMock.login.mockReset();
    authServiceMock.logout.mockReset();
    authServiceMock.me.mockReset();
    authServiceMock.restoreSession.mockReset();
    tokenStorageMock.getAccessToken.mockReset();
    tokenStorageMock.clear.mockReset();
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

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Owner Teste")).toBeInTheDocument();
    });

    expect(authServiceMock.restoreSession).toHaveBeenCalledOnce();
    expect(authServiceMock.me).toHaveBeenCalledOnce();
  });
});
