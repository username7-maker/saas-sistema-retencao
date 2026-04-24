import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UsersPage } from "../pages/settings/UsersPage";
import { userService } from "../services/userService";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "owner-1", full_name: "Owner Teste", role: "owner" },
  }),
}));

vi.mock("../services/userService", () => ({
  userService: {
    listUsers: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    updateUserProfile: vi.fn(),
    setUserActive: vi.fn(),
  },
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("UsersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(userService.listUsers).mockResolvedValue([
      {
        id: "owner-1",
        gym_id: "gym-1",
        full_name: "Owner Teste",
        email: "owner@teste.com",
        role: "owner",
        is_active: true,
        work_shift: null,
        created_at: "2026-03-01T00:00:00Z",
      },
      {
        id: "trainer-1",
        gym_id: "gym-1",
        full_name: "Trainer Teste",
        email: "trainer@teste.com",
        role: "trainer",
        is_active: true,
        work_shift: "morning",
        created_at: "2026-03-02T00:00:00Z",
      },
    ]);
  });

  it("renders trainer users and owner management affordances", async () => {
    renderPage();

    expect(await screen.findByText("Trainer Teste")).toBeInTheDocument();
    expect(screen.getAllByText("Instrutor").length).toBeGreaterThan(0);
    expect(screen.getByText("Turno Manha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Novo usu/i })).toBeInTheDocument();
    expect(screen.getByText(/Owner pode alterar pap/i)).toBeInTheDocument();
  });

  it("uses deactivation language and the activation endpoint flow", async () => {
    vi.mocked(userService.setUserActive).mockResolvedValue({
      id: "trainer-1",
      gym_id: "gym-1",
      full_name: "Trainer Teste",
      email: "trainer@teste.com",
      role: "trainer",
      is_active: false,
      work_shift: "morning",
      created_at: "2026-03-02T00:00:00Z",
    });

    renderPage();

    expect(await screen.findByText("Trainer Teste")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Desativar" }));

    expect(screen.getByText(/acesso ao sistema agora/i)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Desativar" })[1]);

    await waitFor(() => {
      expect(userService.setUserActive).toHaveBeenCalledWith("trainer-1", false);
    });
  });
});
