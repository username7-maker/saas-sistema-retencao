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
    uploadUserAvatar: vi.fn(),
    setUserActive: vi.fn(),
    resetUserPassword: vi.fn(),
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
    expect(screen.getByText(/Owner altera papeis/i)).toBeInTheDocument();
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
      setup_status: "manual_password_set" as const,
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

    fireEvent.change(await screen.findByDisplayValue("Todos os papeis"), { target: { value: "trainer" } });
    expect(await screen.findByText("Nenhum usuario com papel Instrutor neste filtro.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Novo usu/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome do colaborador"), { target: { value: "Gerente Novo" } });
    fireEvent.change(screen.getByPlaceholderText("email@academia.com"), { target: { value: "gerente.novo@teste.com" } });
    fireEvent.change(screen.getByPlaceholderText("Minimo de 8 caracteres"), { target: { value: "SenhaManual123" } });
    fireEvent.change(screen.getByPlaceholderText("Repita a senha"), { target: { value: "SenhaManual123" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar usuario" }));

    await waitFor(() => {
      expect(userService.createUser).toHaveBeenCalled();
    });
    expect(vi.mocked(userService.createUser).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        full_name: "Gerente Novo",
        email: "gerente.novo@teste.com",
        role: "manager",
        password_setup: "manual",
        password: "SenhaManual123",
      }),
    );
    expect(await screen.findByText("Gerente Novo")).toBeInTheDocument();
    expect(screen.getByLabelText("Filtrar por papel")).toHaveValue("manager");
    expect(screen.queryByText("TempPass1234")).not.toBeInTheDocument();
  });

  it("only generates a temporary password on create when explicitly requested", async () => {
    const createdUser = {
      id: "trainer-2",
      gym_id: "gym-1",
      full_name: "Instrutor Novo",
      email: "instrutor.novo@teste.com",
      role: "trainer" as const,
      is_active: true,
      work_shift: null,
      created_at: "2026-03-03T00:00:00Z",
      temporary_password: "TempPass1234",
      setup_status: "temporary_password_generated" as const,
    };

    vi.mocked(userService.createUser).mockResolvedValue(createdUser);

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /Novo usu/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome do colaborador"), { target: { value: "Instrutor Novo" } });
    fireEvent.change(screen.getByPlaceholderText("email@academia.com"), { target: { value: "instrutor.novo@teste.com" } });
    fireEvent.change(screen.getByDisplayValue("Digitar senha agora"), { target: { value: "temporary" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar usuario" }));

    await waitFor(() => {
      expect(userService.createUser).toHaveBeenCalled();
    });
    expect(vi.mocked(userService.createUser).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        email: "instrutor.novo@teste.com",
        password_setup: "temporary",
      }),
    );
    expect(await screen.findByText("TempPass1234")).toBeInTheDocument();
  });

  it("can send an invite link instead of typing a password", async () => {
    const createdUser = {
      id: "trainer-3",
      gym_id: "gym-1",
      full_name: "Convidado Novo",
      email: "convidado.novo@teste.com",
      role: "trainer" as const,
      is_active: true,
      work_shift: null,
      created_at: "2026-03-03T00:00:00Z",
      setup_status: "invite_sent" as const,
    };

    vi.mocked(userService.createUser).mockResolvedValue(createdUser);

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /Novo usu/i }));
    fireEvent.change(screen.getByPlaceholderText("Nome do colaborador"), { target: { value: "Convidado Novo" } });
    fireEvent.change(screen.getByPlaceholderText("email@academia.com"), { target: { value: "convidado.novo@teste.com" } });
    fireEvent.change(screen.getByDisplayValue("Digitar senha agora"), { target: { value: "invite" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar usuario" }));

    await waitFor(() => {
      expect(userService.createUser).toHaveBeenCalled();
    });
    expect(vi.mocked(userService.createUser).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        email: "convidado.novo@teste.com",
        password_setup: "invite",
        password: null,
      }),
    );
  });

  it("lets an owner reset a trainer password and shows the temporary password once", async () => {
    vi.mocked(userService.resetUserPassword).mockResolvedValue({ temporary_password: "ResetPass123" });

    renderPage();

    expect(await screen.findByText("Trainer Teste")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Resetar senha" }));
    fireEvent.click(screen.getByRole("button", { name: "Gerar senha provisoria" }));

    await waitFor(() => {
      expect(userService.resetUserPassword).toHaveBeenCalledWith("trainer-1");
    });
    expect(await screen.findByText("ResetPass123")).toBeInTheDocument();
  });

  it("uploads a team avatar from the edit drawer without asking for an image URL", async () => {
    vi.mocked(userService.uploadUserAvatar).mockResolvedValue({
      id: "trainer-1",
      gym_id: "gym-1",
      full_name: "Trainer Teste",
      email: "trainer@teste.com",
      role: "trainer",
      is_active: true,
      work_shift: "morning",
      avatar_url: "data:image/png;base64,avatar",
      created_at: "2026-03-02T00:00:00Z",
    });

    renderPage();

    expect(await screen.findByText("Trainer Teste")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(screen.getByText(/Cargo e foto mudam a identidade exibida/i)).toBeInTheDocument();
    expect(screen.queryByText("URL da foto")).not.toBeInTheDocument();

    const file = new File(["avatar-bytes"], "avatar.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("Escolher imagem"), { target: { files: [file] } });

    await waitFor(() => {
      expect(userService.uploadUserAvatar).toHaveBeenCalledWith("trainer-1", file);
    });
  });
});
