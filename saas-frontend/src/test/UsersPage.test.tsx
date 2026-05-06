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

  it("shows a newly created user even when another role filter was active", async () => {
    const createdUser = {
      id: "manager-2",
      gym_id: "gym-1",
      full_name: "Gerente Novo",
      email: "gerente.novo@teste.com",
      role: "manager" as const,
      is_active: true,
      work_shift: "afternoon" as const,
      created_at: "2026-03-03T00:00:00Z",
    };

    vi.mocked(userService.listUsers)
      .mockResolvedValueOnce([
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
      ])
      .mockResolvedValue([
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
        createdUser,
      ]);
    vi.mocked(userService.createUser).mockResolvedValue(createdUser);

    renderPage();

    fireEvent.change(await screen.findByDisplayValue("Todos os papéis"), { target: { value: "trainer" } });
    expect(await screen.findByText("Nenhum usuário com papel Instrutor neste filtro.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Novo usu/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome do colaborador"), { target: { value: "Gerente Novo" } });
    fireEvent.change(screen.getByPlaceholderText("email@academia.com"), { target: { value: "gerente.novo@teste.com" } });
    fireEvent.change(screen.getByPlaceholderText(/8 caracteres/i), { target: { value: "senha1234" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar usuário" }));

    await waitFor(() => {
      expect(userService.createUser).toHaveBeenCalled();
    });
    expect(vi.mocked(userService.createUser).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        full_name: "Gerente Novo",
        email: "gerente.novo@teste.com",
        role: "manager",
      }),
    );
    expect(await screen.findByText("Gerente Novo")).toBeInTheDocument();
    expect(screen.getByLabelText("Filtrar por papel")).toHaveValue("manager");
  });
});
