import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AITriageInboxPage from "../pages/ai/AITriageInboxPage";
import { aiTriageService } from "../services/aiTriageService";
import type { AITriageRecommendation } from "../types";

let currentUserMock = { id: "user-1", full_name: "Julia Operacoes", work_shift: null as "morning" | "afternoon" | "evening" | null };

vi.mock("../services/aiTriageService", () => ({
  aiTriageService: {
    getMetricsSummary: vi.fn(),
    listItems: vi.fn(),
    getItem: vi.fn(),
    updateApproval: vi.fn(),
    prepareAction: vi.fn(),
    updateOutcome: vi.fn(),
  },
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: currentUserMock,
    loading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

function makeRecommendation(overrides?: Partial<AITriageRecommendation>): AITriageRecommendation {
  return {
    id: "rec-1",
    source_domain: "retention",
    source_entity_kind: "member",
    source_entity_id: "member-1",
    member_id: "member-1",
    lead_id: null,
    subject_name: "Ana Silva",
    priority_score: 92,
    priority_bucket: "critical",
    why_now_summary: "16 dias sem check-in e forecast baixo.",
    why_now_details: ["Risco atual: red.", "16 dias sem check-in."],
    recommended_action: "Ligar hoje",
    recommended_channel: "call",
    recommended_owner: { user_id: "user-1", role: "manager", label: "Julia Operacoes" },
    suggested_message: "Oi Ana, vamos retomar sua rotina.",
    expected_impact: "Evitar cancelamento nas proximas 48 horas.",
    operator_summary: "16 dias sem check-in e forecast baixo.",
    primary_action_type: "prepare_outbound_message",
    primary_action_label: "Preparar ligacao",
    requires_explicit_approval: true,
    show_outcome_step: false,
    suggestion_state: "suggested",
    approval_state: "pending",
    execution_state: "pending",
    outcome_state: "pending",
    metadata: { risk_level: "red", forecast_60d: 35, preferred_shift: "morning" },
    last_refreshed_at: "2026-04-18T12:00:00Z",
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/ai/triage"]}>
        <Routes>
          <Route path="/ai/triage" element={<AITriageInboxPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AITriageInboxPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUserMock = { id: "user-1", full_name: "Julia Operacoes", work_shift: null };
    vi.mocked(aiTriageService.getMetricsSummary).mockResolvedValue({
      total_active: 1,
      pending_approval_total: 1,
      approved_total: 0,
      rejected_total: 0,
      prepared_action_total: 0,
      positive_outcome_total: 0,
      neutral_outcome_total: 0,
      negative_outcome_total: 0,
      acceptance_rate: null,
      average_time_to_approval_seconds: null,
      median_time_to_approval_seconds: null,
      same_day_prepared_total: 0,
    });
  });

  it("prepares a normal item with auto approval in one click", async () => {
    const recommendation = makeRecommendation({
      id: "rec-normal",
      priority_score: 58,
      priority_bucket: "medium",
      requires_explicit_approval: false,
      primary_action_label: "Preparar WhatsApp",
      recommended_channel: "whatsapp",
      approval_state: "pending",
      operator_summary: "Primeiro follow-up do onboarding ainda nao aconteceu.",
      source_domain: "onboarding",
    });
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [recommendation],
      total: 1,
      page: 1,
      page_size: 50,
    });
    vi.mocked(aiTriageService.getItem).mockResolvedValue(recommendation);
    vi.mocked(aiTriageService.prepareAction).mockResolvedValue({
      recommendation: {
        ...recommendation,
        approval_state: "approved",
        execution_state: "prepared",
        show_outcome_step: true,
      },
      action: "prepare_outbound_message",
      supported: true,
      detail: "Mensagem preparada para revisao humana antes do envio.",
      task_id: null,
      follow_up_url: null,
      prepared_message: "Oi Ana, vamos retomar sua rotina.",
      metadata: {},
    });

    renderPage();

    expect(await screen.findByText("Fila de execucao")).toBeInTheDocument();
    expect((await screen.findAllByText("Ana Silva")).length).toBeGreaterThan(0);
    const operatorNoteInput = screen.getByPlaceholderText("Observacao opcional para esta acao");
    fireEvent.change(operatorNoteInput, {
      target: { value: "Pode seguir agora." },
    });
    await waitFor(() => expect(operatorNoteInput).toHaveValue("Pode seguir agora."));
    fireEvent.click(screen.getAllByRole("button", { name: /preparar whatsapp/i })[1]);

    await waitFor(() => {
      expect(aiTriageService.prepareAction).toHaveBeenCalledWith("rec-normal", {
        action: "prepare_outbound_message",
        operator_note: "Pode seguir agora.",
        auto_approve: true,
        confirm_approval: undefined,
      });
    });
  });

  it("requires explicit confirmation for a critical item before preparing the action", async () => {
    const recommendation = makeRecommendation();
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [recommendation],
      total: 1,
      page: 1,
      page_size: 50,
    });
    vi.mocked(aiTriageService.getItem).mockResolvedValue(recommendation);
    vi.mocked(aiTriageService.prepareAction).mockResolvedValue({
      recommendation: {
        ...recommendation,
        approval_state: "approved",
        execution_state: "prepared",
        show_outcome_step: true,
      },
      action: "prepare_outbound_message",
      supported: true,
      detail: "Mensagem preparada para revisao humana antes do envio.",
      task_id: null,
      follow_up_url: null,
      prepared_message: "Oi Ana, vamos retomar sua rotina.",
      metadata: {},
    });

    renderPage();

    expect((await screen.findAllByText("Ana Silva")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /aprovar e preparar acao/i }));
    expect(await screen.findByText("Confirmar aprovacao e preparar a acao agora?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /confirmar e preparar/i }));

    await waitFor(() => {
      expect(aiTriageService.prepareAction).toHaveBeenCalledWith("rec-1", {
        action: "prepare_outbound_message",
        operator_note: undefined,
        auto_approve: undefined,
        confirm_approval: true,
      });
    });
  });

  it("still requires explicit confirmation when a critical item comes without the explicit flag", async () => {
    const recommendation = makeRecommendation({
      id: "rec-critical-fallback",
      requires_explicit_approval: false,
      primary_action_label: null as unknown as string,
      primary_action_type: null as unknown as "prepare_outbound_message",
      source_domain: "onboarding",
      recommended_action: "Concluir primeira avaliacao de onboarding",
      recommended_channel: "task",
      suggested_message: "Agendar a primeira avaliacao para destravar a jornada inicial do aluno.",
    });
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [recommendation],
      total: 1,
      page: 1,
      page_size: 50,
    });
    vi.mocked(aiTriageService.getItem).mockResolvedValue(recommendation);
    vi.mocked(aiTriageService.prepareAction).mockResolvedValue({
      recommendation: {
        ...recommendation,
        approval_state: "approved",
        execution_state: "prepared",
        show_outcome_step: true,
      },
      action: "create_task",
      supported: true,
      detail: "Tarefa preparada para acompanhamento da avaliacao.",
      task_id: "task-1",
      follow_up_url: null,
      prepared_message: null,
      metadata: {},
    });

    renderPage();

    expect((await screen.findAllByText("Ana Silva")).length).toBeGreaterThan(0);
    expect(await screen.findByRole("button", { name: /aprovar e preparar acao/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /aprovar e preparar acao/i }));
    fireEvent.click(await screen.findByRole("button", { name: /confirmar e preparar/i }));

    await waitFor(() => {
      expect(aiTriageService.prepareAction).toHaveBeenCalledWith("rec-critical-fallback", {
        action: "create_task",
        operator_note: undefined,
        auto_approve: undefined,
        confirm_approval: true,
      });
    });
  });

  it("falls back to explicit approval plus prepare when the API returns 409 on prepare", async () => {
    const recommendation = makeRecommendation({
      id: "rec-critical-409",
      source_domain: "onboarding",
      recommended_action: "Concluir primeira avaliacao de onboarding",
      recommended_channel: "task",
      primary_action_type: "create_task",
      primary_action_label: "Criar tarefa",
    });
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [recommendation],
      total: 1,
      page: 1,
      page_size: 50,
    });
    vi.mocked(aiTriageService.getItem).mockResolvedValue(recommendation);
    vi.mocked(aiTriageService.prepareAction)
      .mockRejectedValueOnce({
        response: {
          status: 409,
          data: { detail: "Recommendation critica ou degradada exige confirmacao explicita antes da acao." },
        },
      })
      .mockResolvedValueOnce({
        recommendation: {
          ...recommendation,
          approval_state: "approved",
          execution_state: "prepared",
          show_outcome_step: true,
        },
        action: "create_task",
        supported: true,
        detail: "Tarefa preparada para acompanhamento.",
        task_id: "task-1",
        follow_up_url: null,
        prepared_message: null,
        metadata: {},
      });
    vi.mocked(aiTriageService.updateApproval).mockResolvedValue({
      ...recommendation,
      approval_state: "approved",
    });

    renderPage();

    expect((await screen.findAllByText("Ana Silva")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /aprovar e preparar acao/i }));
    fireEvent.click(await screen.findByRole("button", { name: /confirmar e preparar/i }));

    await waitFor(() => {
      expect(aiTriageService.updateApproval).toHaveBeenCalledWith("rec-critical-409", {
        decision: "approved",
        note: undefined,
      });
      expect(aiTriageService.prepareAction).toHaveBeenNthCalledWith(2, "rec-critical-409", {
        action: "create_task",
        operator_note: undefined,
      });
    });
  });

  it("registers outcome from the awaiting result view", async () => {
    const recommendation = makeRecommendation({
      id: "rec-outcome",
      approval_state: "approved",
      execution_state: "prepared",
      show_outcome_step: true,
      requires_explicit_approval: false,
    });
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [recommendation],
      total: 1,
      page: 1,
      page_size: 50,
    });
    vi.mocked(aiTriageService.getItem).mockResolvedValue(recommendation);
    vi.mocked(aiTriageService.updateOutcome).mockResolvedValue({
      ...recommendation,
      execution_state: "completed",
      outcome_state: "positive",
    });

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /aguardando resultado \(1\)/i }));
    expect(await screen.findByText("Registrar resultado")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Observacao opcional para esta acao"), {
      target: { value: "Aluno respondeu no mesmo dia." },
    });
    fireEvent.click(screen.getByRole("button", { name: /marcar positivo/i }));

    await waitFor(() => {
      expect(aiTriageService.updateOutcome).toHaveBeenCalledWith("rec-outcome", {
        outcome: "positive",
        note: "Aluno respondeu no mesmo dia.",
      });
    });
  });

  it("renders the empty state when there are no active recommendations", async () => {
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
    });

    renderPage();

    expect(await screen.findByText("Nenhuma recommendation ativa")).toBeInTheDocument();
  });

  it("renders the degraded error state when the list fails", async () => {
    vi.mocked(aiTriageService.listItems).mockRejectedValue(new Error("boom"));

    renderPage();

    expect(await screen.findByText("Erro ao carregar a inbox AI-first")).toBeInTheDocument();
  });

  it("falls back to the first filtered item while the detail request is still pending", async () => {
    const recommendation = makeRecommendation();
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [recommendation],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(aiTriageService.getItem).mockImplementation(() => new Promise(() => {}));

    renderPage();

    expect(await screen.findByText("Fazer agora")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /aprovar e preparar acao/i })).toBeInTheDocument();
  });

  it("defaults the inbox to the logged-in shift and allows opening all shifts", async () => {
    currentUserMock = { id: "user-1", full_name: "Julia Operacoes", work_shift: "morning" };
    vi.mocked(aiTriageService.listItems).mockResolvedValue({
      items: [
        makeRecommendation({ id: "rec-1", subject_name: "Ana Silva", metadata: { preferred_shift: "morning" } }),
        makeRecommendation({ id: "rec-2", subject_name: "Bruno Noite", metadata: { preferred_shift: "evening" } }),
      ],
      total: 2,
      page: 1,
      page_size: 50,
    });
    vi.mocked(aiTriageService.getItem).mockResolvedValue(makeRecommendation({ metadata: { preferred_shift: "morning" } }));

    renderPage();

    expect(await screen.findByRole("button", { name: "Meu turno: Manha" })).toBeInTheDocument();
    expect((await screen.findAllByText("Ana Silva")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Bruno Noite")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Meu turno: Manha" }));

    expect(await screen.findByRole("button", { name: "Todos os turnos" })).toBeInTheDocument();
    expect(screen.getByText("Bruno Noite")).toBeInTheDocument();
  });
});
