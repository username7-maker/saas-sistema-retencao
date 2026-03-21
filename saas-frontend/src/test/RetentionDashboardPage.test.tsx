import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RetentionDashboardPage } from "../pages/dashboard/RetentionDashboardPage";
import { useRetentionDashboard } from "../hooks/useDashboard";
import { dashboardService, type RetentionQueueItem, type RetentionQueueResponse } from "../services/dashboardService";
import { riskAlertService } from "../services/riskAlertService";

vi.mock("../hooks/useDashboard", () => ({
  useRetentionDashboard: vi.fn(),
}));

vi.mock("../services/dashboardService", async () => {
  const actual = await vi.importActual<typeof import("../services/dashboardService")>("../services/dashboardService");
  return {
    ...actual,
    dashboardService: {
      ...actual.dashboardService,
      retentionQueue: vi.fn(),
    },
  };
});

vi.mock("../services/riskAlertService", () => ({
  riskAlertService: {
    resolve: vi.fn(),
  },
}));

vi.mock("../components/common/AiInsightCard", () => ({
  AiInsightCard: () => <div>Insight automático</div>,
}));

vi.mock("../components/common/DashboardActions", () => ({
  DashboardActions: () => <button type="button">Exportar PDF</button>,
}));

vi.mock("../components/common/QuickActions", () => ({
  QuickActions: () => <div>Ações rápidas mock</div>,
}));

function queryResult<T>(data: T) {
  return {
    data,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  };
}

function createQueueItem(id: string, overrides: Partial<RetentionQueueItem> = {}): RetentionQueueItem {
  return {
    alert_id: `alert-${id}`,
    member_id: id,
    full_name: `Aluno ${id}`,
    email: `${id}@teste.com`,
    phone: "5511999990001",
    plan_name: "Plano Premium",
    risk_level: "red",
    risk_score: 82,
    nps_last_score: 6,
    days_without_checkin: 10,
    last_checkin_at: "2026-03-10T10:00:00Z",
    last_contact_at: "2026-03-15T10:00:00Z",
    churn_type: "voluntary_dissatisfaction",
    automation_stage: "d14",
    created_at: "2026-03-12T10:00:00Z",
    forecast_60d: 34,
    signals_summary: "10 dias sem check-in · queda de 62% na frequência",
    next_action: "Mensagem de reengajamento",
    reasons: { frequency_drop_pct: 62 },
    action_history: [],
    playbook_steps: [
      {
        action: "whatsapp",
        priority: "high",
        title: "Mensagem de reengajamento",
        message: "Retome o treino esta semana.",
        due_days: 0,
        owner: "reception",
      },
    ],
    assistant: {
      summary: `Aluno ${id} entrou na fila por sinais fortes de evasao.`,
      why_it_matters: "Sem resposta rapida, a chance de recuperar o aluno cai.",
      next_best_action: "Abrir o perfil e executar o primeiro playbook.",
      suggested_message: "Oi, quero te ajudar a retomar o ritmo desta semana.",
      evidence: ["10 dias sem check-in", "queda de 62% na frequencia"],
      confidence_label: "Alta",
      recommended_channel: "Ligacao",
      cta_target: `/assessments/members/${id}?tab=contexto`,
      cta_label: "Abrir perfil 360",
    },
    ...overrides,
  };
}

const retentionSummary = {
  red: { total: 284, items: [] },
  yellow: { total: 4, items: [] },
  nps_trend: [],
  mrr_at_risk: 15800,
  avg_red_score: 76,
  avg_yellow_score: 48,
  churn_distribution: {
    voluntary_dissatisfaction: 120,
    involuntary_inactivity: 88,
    voluntary_financial: 44,
    unknown: 36,
  },
  last_contact_map: {},
};

const queuePage1: RetentionQueueResponse = {
  items: [
    createQueueItem("member-1", { full_name: "Ana Silva" }),
    createQueueItem("member-2", { full_name: "Bruno Lima", risk_level: "yellow", risk_score: 51, forecast_60d: 58 }),
  ],
  total: 3,
  page: 1,
  page_size: 2,
};

const queuePage2: RetentionQueueResponse = {
  items: [createQueueItem("member-3", { full_name: "Carla Nunes" })],
  total: 3,
  page: 2,
  page_size: 2,
};

const yellowOnly: RetentionQueueResponse = {
  items: [createQueueItem("member-4", { full_name: "Daniel Costa", risk_level: "yellow", risk_score: 45 })],
  total: 1,
  page: 1,
  page_size: 50,
};

const searchResult: RetentionQueueResponse = {
  items: [createQueueItem("member-5", { full_name: "Erica Santos" })],
  total: 1,
  page: 1,
  page_size: 50,
};

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
        <RetentionDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RetentionDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useRetentionDashboard).mockReturnValue(queryResult(retentionSummary) as never);
    vi.mocked(riskAlertService.resolve).mockResolvedValue({
      id: "resolved-alert",
      member_id: "member-1",
      score: 82,
      level: "red",
      reasons: {},
      action_history: [],
      automation_stage: "d14",
      resolved: true,
      created_at: "2026-03-12T10:00:00Z",
    } as never);

    vi.mocked(dashboardService.retentionQueue).mockImplementation(async (params) => {
      if (params?.search === "Erica") return searchResult;
      if (params?.level === "yellow") return yellowOnly;
      if (params?.page === 2) return queuePage2;
      return queuePage1;
    });
  });

  it("renders executive summary, queue and opens playbook drawer on demand", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Retenção" })).toBeInTheDocument();
    expect(screen.getByText("Insight automático")).toBeInTheDocument();
    expect(screen.getByText("Fila operacional")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Ana Silva/i })).toBeInTheDocument();
    expect(screen.getByText("Página 1 de 2")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /^Ver playbook$/i })[0]);

    expect(await screen.findByText("Playbook sugerido")).toBeInTheDocument();
    expect(screen.getByText("Copiloto de retenção")).toBeInTheDocument();
    expect(screen.getByText("Mensagem de reengajamento")).toBeInTheDocument();
    expect(screen.getByText("Ações rápidas mock")).toBeInTheDocument();
  });

  it("uses server-side search and resets pagination when filters change", async () => {
    renderPage();

    await screen.findByRole("button", { name: /Ana Silva/i });
    fireEvent.click(screen.getByRole("button", { name: /^Proximo$/i }));
    await waitFor(() => {
      expect(dashboardService.retentionQueue).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 2 }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("Buscar por nome, e-mail ou plano do aluno..."), {
      target: { value: "Erica" },
    });

    await waitFor(() => {
      expect(dashboardService.retentionQueue).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "Erica", page: 1 }),
      );
    });

    fireEvent.change(screen.getByLabelText("Severidade"), {
      target: { value: "yellow" },
    });

    await waitFor(() => {
      expect(dashboardService.retentionQueue).toHaveBeenLastCalledWith(
        expect.objectContaining({ level: "yellow", page: 1 }),
      );
    });
  }, 10000);

  it("resolves an alert from the queue actions", async () => {
    renderPage();

    await screen.findByRole("button", { name: /Ana Silva/i });
    fireEvent.click(screen.getAllByRole("button", { name: /^Resolver$/i })[0]);

    await waitFor(() => {
      expect(riskAlertService.resolve).toHaveBeenCalledWith("alert-member-1", "Resolvido no dashboard de retenção");
    });
  });
});
