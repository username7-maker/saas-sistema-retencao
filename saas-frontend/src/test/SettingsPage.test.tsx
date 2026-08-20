import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "../pages/settings/SettingsPage";
import { api } from "../services/api";
import { userService } from "../services/userService";

const mocks = vi.hoisted(() => ({
  logout: vi.fn(),
  refreshUser: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "owner-1",
      full_name: "Owner Teste",
      email: "owner@teste.com",
      role: "owner",
      job_title: "Gestor",
      avatar_url: null,
    },
    logout: mocks.logout,
    refreshUser: mocks.refreshUser,
  }),
}));

vi.mock("../services/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

vi.mock("../services/userService", () => ({
  userService: {
    updateMyProfile: vi.fn(),
    updateMyPassword: vi.fn(),
    uploadMyAvatar: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  default: {
    error: mocks.toastError,
    success: mocks.toastSuccess,
  },
}));

vi.mock("../components/settings/ActuarConnectionTab", () => ({
  ActuarConnectionTab: () => <div>Actuar mock</div>,
}));

vi.mock("../components/settings/AiServiceAgentSettingsTab", () => ({
  AiServiceAgentSettingsTab: () => <div>Agent mock</div>,
}));

vi.mock("../components/settings/AutopilotSettingsTab", () => ({
  AutopilotSettingsTab: () => <div>Autopilot mock</div>,
}));

vi.mock("../components/settings/KommoConnectionTab", () => ({
  KommoConnectionTab: () => <div>Kommo mock</div>,
}));

vi.mock("../components/settings/MovementVideoSettingsTab", () => ({
  MovementVideoSettingsTab: () => <div>Motion mock</div>,
}));

vi.mock("../components/settings/PersonalAiSettingsTab", () => ({
  PersonalAiSettingsTab: () => <div>Coach mock</div>,
}));

vi.mock("../components/settings/StudentPersonalAiSettingsTab", () => ({
  StudentPersonalAiSettingsTab: () => <div>Aluno mock</div>,
}));

vi.mock("../components/settings/WhatsAppConnectionTab", () => ({
  WhatsAppConnectionTab: () => <div>WhatsApp mock</div>,
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
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.logout.mockResolvedValue(undefined);
    vi.mocked(userService.updateMyPassword).mockResolvedValue({ message: "ok" });
    vi.mocked(userService.uploadMyAvatar).mockResolvedValue({
      id: "owner-1",
      gym_id: "gym-1",
      full_name: "Owner Teste",
      email: "owner@teste.com",
      role: "owner",
      is_active: true,
      job_title: "Gestor",
      avatar_url: "data:image/png;base64,avatar",
      created_at: "2026-03-01T00:00:00Z",
    });
    vi.mocked(api.post).mockResolvedValue({ data: { message: "ok" } });
  });

  it("lets an authenticated user change their own password and logs out", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Seguranca" }));
    fireEvent.change(screen.getByPlaceholderText("Senha atual"), { target: { value: "Current123" } });
    fireEvent.change(screen.getByPlaceholderText("Minimo de 8 caracteres"), { target: { value: "NewSecret123" } });
    fireEvent.change(screen.getByPlaceholderText("Repita a nova senha"), { target: { value: "NewSecret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Alterar senha" }));

    await waitFor(() => {
      expect(userService.updateMyPassword).toHaveBeenCalledWith({
        current_password: "Current123",
        new_password: "NewSecret123",
      });
    });
    expect(mocks.toastSuccess).toHaveBeenCalledWith("Senha atualizada. Entre novamente com a nova senha.");
    await waitFor(() => {
      expect(mocks.logout).toHaveBeenCalled();
    });
  });

  it("keeps e-mail recovery as a fallback path with provider failure guidance", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Seguranca" }));

    expect(screen.getByText("Recuperacao por e-mail")).toBeInTheDocument();
    expect(screen.getByText(/Se o provedor de e-mail bloquear o envio/i)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("minha-academia"), { target: { value: "ai-gym-os-piloto" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar link" }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/forgot-password", {
        email: "owner@teste.com",
        gym_slug: "ai-gym-os-piloto",
      });
    });
  });

  it("uses file upload as the primary profile avatar path", async () => {
    renderPage();

    expect(screen.getByText("Enviar foto do perfil")).toBeInTheDocument();
    expect(screen.getByText("Origem alternativa da foto")).toBeInTheDocument();

    const file = new File(["avatar-bytes"], "avatar.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("Escolher imagem"), { target: { files: [file] } });

    await waitFor(() => {
      expect(userService.uploadMyAvatar).toHaveBeenCalledWith(file);
    });
    expect(mocks.refreshUser).toHaveBeenCalled();
  });
});
