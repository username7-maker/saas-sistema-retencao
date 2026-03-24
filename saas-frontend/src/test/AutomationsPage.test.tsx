import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AutomationsPage } from "../pages/automations/AutomationsPage";
import { automationService } from "../services/automationService";

let mockRole: "owner" | "manager" = "owner";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "user-1", full_name: "Usuário Teste", role: mockRole },
  }),
}));

vi.mock("../services/automationService", () => ({
  automationService: {
    listRules: vi.fn(),
    createRule: vi.fn(),
    updateRule: vi.fn(),
    deleteRule: vi.fn(),
    executeAll: vi.fn(),
    seedDefaults: vi.fn(),
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
        <AutomationsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AutomationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRole = "owner";
    vi.mocked(automationService.executeAll).mockResolvedValue([]);
    vi.mocked(automationService.seedDefaults).mockResolvedValue([]);
  });

  it("hides owner-only controls from manager", async () => {
    mockRole = "manager";
    vi.mocked(automationService.listRules).mockResolvedValue([
      {
        id: "rule-1",
        name: "Reengajar inativos",
        description: "Dispara mensagem após 7 dias.",
        trigger_type: "inactivity_days",
        trigger_config: { days: 7 },
        action_type: "send_whatsapp",
        action_config: { template: "custom", message: "Oi" },
        is_active: true,
        executions_count: 4,
        last_executed_at: null,
        created_at: "2026-03-20T00:00:00Z",
        updated_at: "2026-03-20T00:00:00Z",
      },
    ]);

    renderPage();

    expect(await screen.findByText("Reengajar inativos")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Excluir Reengajar inativos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Regras Padrão" })).not.toBeInTheDocument();
  });

  it("keeps owner controls visible", async () => {
    vi.mocked(automationService.listRules).mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText("Nenhuma regra configurada")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Regras Padrão" }).length).toBeGreaterThan(0);
  });
});
