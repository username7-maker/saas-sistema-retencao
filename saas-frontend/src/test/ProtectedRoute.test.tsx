import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "../components/common/ProtectedRoute";

const useAuthMock = vi.fn();

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => useAuthMock(),
}));

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users to login", () => {
    useAuthMock.mockReturnValue({
      user: null,
      loading: false,
      isAuthenticated: false,
    });

    render(
      <MemoryRouter initialEntries={["/members"]}>
        <Routes>
          <Route
            path="/members"
            element={(
              <ProtectedRoute>
                <div>Members</div>
              </ProtectedRoute>
            )}
          />
          <Route path="/login" element={<div>Login</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Login")).toBeInTheDocument();
  });

  it("redirects trainer away from user admin routes", () => {
    useAuthMock.mockReturnValue({
      user: { id: "trainer-1", full_name: "Treinador", role: "trainer" },
      loading: false,
      isAuthenticated: true,
    });

    render(
      <MemoryRouter initialEntries={["/settings/users"]}>
        <Routes>
          <Route
            path="/settings/users"
            element={(
              <ProtectedRoute allowedRoles={["owner", "manager"]}>
                <div>User Admin</div>
              </ProtectedRoute>
            )}
          />
          <Route path="/assessments" element={<div>Assessments Home</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Assessments Home")).toBeInTheDocument();
  });
});
