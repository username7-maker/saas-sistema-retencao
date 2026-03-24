import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
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
        created_at: "2026-03-01T00:00:00Z",
      },
      {
        id: "trainer-1",
        gym_id: "gym-1",
        full_name: "Trainer Teste",
        email: "trainer@teste.com",
        role: "trainer",
        is_active: true,
        created_at: "2026-03-02T00:00:00Z",
      },
    ]);
  });

  it("renders trainer users and offers trainer in the create form", async () => {
    renderPage();

    expect(await screen.findByText("Trainer Teste")).toBeInTheDocument();
    expect(screen.getAllByText("Instrutor").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /Novo Usuário/i }));

    expect(await screen.findByRole("heading", { name: "Novo Usuário" })).toBeInTheDocument();
    expect(screen.getAllByRole("option", { name: "Instrutor" }).length).toBeGreaterThan(1);
  });
});
