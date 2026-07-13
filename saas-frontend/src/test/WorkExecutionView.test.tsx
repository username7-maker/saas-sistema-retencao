import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WorkExecutionView } from "../components/workQueue/WorkExecutionView";
import { memberService } from "../services/memberService";
import { taskService } from "../services/taskService";
import { workQueueService } from "../services/workQueueService";
import type { LeadToMemberIntelligenceContext, WorkQueueActionResult, WorkQueueItem, WorkQueueListResponse } from "../types";

const TASK_CANONICAL_ID = "33333333-3333-3333-3333-333333333333";

vi.mock("../services/workQueueService", () => ({
  workQueueService: {
    listItems: vi.fn(),
    getItem: vi.fn(),
    executeItem: vi.fn(),
    updateOutcome: vi.fn(),
    sendAndWait: vi.fn(),
    regenerateMessage: vi.fn(),
  },
}));

vi.mock("../services/memberService", () => ({
  memberService: {
    getIntelligenceContext: vi.fn(),
  },
}));

vi.mock("../services/taskService", () => ({
  taskService: {
    createEvent: vi.fn(),
  },
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "user-1",
      full_name: "Operadora Sintetica",
      role: "manager",
      work_shift: "morning",
      work_shift_scope: null,
    },
  }),
}));

function makeItem(overrides: Record<string, unknown> = {}): WorkQueueItem {
  return {
    source_type: "ai_triage",
    source_id: "rec-1",
    subject_name: "Ana Sintetica",
    member_id: "member-1",
    lead_id: null,
    subject_phone: "+5554999990000",
    domain: "onboarding",
    severity: "high",
    preferred_shift: "morning",
    preferred_shift_status: "resolved_from_checkins",
    preferred_shift_reason: null,
    preferred_shift_counts: { morning: 4 },
    reason: "Onboarding precisa de acao coordenada.",
    primary_action_label: "Criar tarefa",
    primary_action_type: "create_task",
    suggested_message: "Oi Ana, vamos ajustar seu plano?",
    message_source: "ai_specialist",
    prompt_key: "synthetic",
    prompt_version: "v1",
    model: "synthetic",
    safety_profile: "safe",
    message_fallback_used: false,
    message_blocked_reasons: [],
    requires_confirmation: false,
    state: "do_now",
    due_at: null,
    visible_from: null,
    assigned_to_user_id: "user-1",
    context_path: "/tasks",
    outcome_state: "pending",
    canonical_task_id: null,
    last_refreshed_at: "2026-07-13T12:00:00Z",
    freshness_state: "fresh",
    freshness_blocking: false,
    readiness_missing_fields: [],
    signal_value: 71,
    priority_state: "known",
    assigned_to_name: "Recepcao Sintetica",
    assigned_to_role: "reception",
    ...overrides,
  } as WorkQueueItem;
}

function makeEnvelope(overrides: Partial<WorkQueueListResponse> = {}): WorkQueueListResponse {
  const items = overrides.items ?? [makeItem()];
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 25,
    state_counts: { do_now: items.length, awaiting_outcome: 0, done: 0 },
    truncated_sources: [],
    ...overrides,
  };
}

function makeResult(item: WorkQueueItem): WorkQueueActionResult {
  return {
    item,
    detail: "Resultado sintetico registrado.",
    prepared_message: item.suggested_message,
    context_path: item.context_path,
    metadata: {},
  };
}

function makeIntelligenceContext(): LeadToMemberIntelligenceContext {
  return {
    version: "lead-member-context-v1",
    generated_at: "2026-07-13T12:00:00Z",
    member: {
      member_id: "member-1",
      full_name: "Ana Sintetica",
      email: "ana@teste.invalid",
      phone: "+5554999990000",
      status: "active",
      plan_name: "Plano Teste",
      monthly_fee: 199,
      join_date: "2026-07-01",
      preferred_shift: "morning",
      assigned_user_id: "user-1",
      is_vip: false,
    },
    lead: null,
    consent: {
      lgpd: true,
      communication: true,
      image: null,
      contract: true,
      source: "synthetic",
      missing: ["image"],
    },
    lifecycle: {
      onboarding_status: "active",
      onboarding_score: 71,
      retention_stage: null,
      churn_type: null,
      loyalty_months: 1,
    },
    activity: {
      last_checkin_at: "2026-07-12T12:00:00Z",
      days_without_checkin: 1,
      checkins_30d: 8,
      checkins_90d: 8,
      preferred_shift: "morning",
    },
    assessment: {
      assessments_total: 0,
      latest_assessment_at: null,
      body_composition_total: 0,
      latest_body_composition_at: null,
      latest_body_fat_percent: null,
      latest_muscle_mass_kg: null,
      latest_weight_kg: null,
    },
    operations: {
      open_tasks_total: 1,
      overdue_tasks_total: 0,
      next_task_due_at: null,
      latest_completed_task_at: null,
    },
    risk: {
      risk_level: "yellow",
      risk_score: 40,
      open_alerts_total: 0,
      nps_last_score: null,
    },
    signals: [],
    data_quality_flags: [],
  };
}

function renderRunner() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <WorkExecutionView source="ai_triage" defaultDomain="all" title="Runner sintetico" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WorkExecutionView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    vi.mocked(memberService.getIntelligenceContext).mockResolvedValue(makeIntelligenceContext());
    vi.mocked(taskService.createEvent).mockResolvedValue({} as never);
    vi.mocked(workQueueService.listItems).mockResolvedValue(makeEnvelope());
    vi.mocked(workQueueService.getItem).mockResolvedValue(makeItem({ source_type: "task", source_id: TASK_CANONICAL_ID }));
    vi.mocked(workQueueService.executeItem).mockResolvedValue(makeResult(makeItem({ state: "awaiting_outcome" })));
    vi.mocked(workQueueService.updateOutcome).mockResolvedValue(makeResult(makeItem({ state: "done" })));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("WQ runner envia busca remota com debounce de 300ms, Enter imediato, clear e page 1", async () => {
    vi.mocked(workQueueService.listItems).mockResolvedValue(makeEnvelope({ items: [makeItem({ subject_name: "Agulha Sintetica" })], total: 1 }));

    renderRunner();

    expect((await screen.findAllByText("Agulha Sintetica")).length).toBeGreaterThan(0);
    vi.useFakeTimers();
    const searchInput = screen.getByPlaceholderText("Buscar aluno, motivo ou acao...");

    fireEvent.change(searchInput, { target: { value: "agulha" } });
    expect(workQueueService.listItems).not.toHaveBeenCalledWith(expect.objectContaining({ q: "agulha" }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(299);
    });
    expect(workQueueService.listItems).not.toHaveBeenCalledWith(expect.objectContaining({ q: "agulha" }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(workQueueService.listItems).toHaveBeenCalledWith(
      expect.objectContaining({ q: "agulha", page: 1, page_size: 25, state: "do_now" }),
    );

    fireEvent.change(searchInput, { target: { value: "bruno" } });
    fireEvent.keyDown(searchInput, { key: "Enter" });
    await act(async () => {
      await Promise.resolve();
    });
    expect(workQueueService.listItems).toHaveBeenCalledWith(expect.objectContaining({ q: "bruno", page: 1 }));

    fireEvent.click(screen.getByRole("button", { name: "Limpar busca" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
      await Promise.resolve();
    });
    expect(workQueueService.listItems).toHaveBeenCalledWith(expect.objectContaining({ page: 1, q: undefined }));
  });

  it("WQ runner usa um unico envelope para contadores, truncamento e pagina 2", async () => {
    vi.mocked(workQueueService.listItems).mockImplementation(async (params) =>
      makeEnvelope({
        items: [makeItem({ source_id: params?.page === 2 ? "rec-26" : "rec-1", subject_name: params?.page === 2 ? "Pagina Dois" : "Pagina Um" })],
        total: 188,
        page: params?.page ?? 1,
        page_size: 25,
        state_counts: { do_now: 188, awaiting_outcome: 7, done: 2 },
        truncated_sources: ["ai_triage"],
      }),
    );

    renderRunner();

    expect((await screen.findAllByText("Pagina Um")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Fazer agora (188+)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aguardando resultado (7)" })).toBeInTheDocument();
    expect(screen.getByText("Mostrando 1-25 de pelo menos 188 acoes")).toBeInTheDocument();
    expect(screen.getByText("Fonte limitada: ai_triage. Total exibido como limite inferior.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Proximo" }));

    await waitFor(() => {
      expect(workQueueService.listItems).toHaveBeenCalledWith(expect.objectContaining({ page: 2, page_size: 25 }));
    });
    expect((await screen.findAllByText("Pagina Dois")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Pagina Dois .*Criar tarefa/i })).toHaveFocus();
    });
    expect(screen.getByText("Mostrando 26-50 de pelo menos 188 acoes")).toBeInTheDocument();
  });

  it("WQ runner continua tarefa canonica read-only sem preparar ou executar a recomendacao", async () => {
    const recommendation = makeItem({
      source_id: "rec-canonical",
      canonical_task_id: TASK_CANONICAL_ID,
      primary_action_label: "Criar tarefa",
    });
    const task = makeItem({
      source_type: "task",
      source_id: TASK_CANONICAL_ID,
      canonical_task_id: TASK_CANONICAL_ID,
      subject_name: "Task Canonica",
      primary_action_label: "Retomar task existente",
    });
    vi.mocked(workQueueService.listItems).mockResolvedValue(makeEnvelope({ items: [recommendation] }));
    vi.mocked(workQueueService.getItem).mockResolvedValue(task);

    renderRunner();

    expect((await screen.findAllByText("Ana Sintetica")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Continuar tarefa" }));

    await waitFor(() => {
      expect(workQueueService.getItem).toHaveBeenCalledWith("task", TASK_CANONICAL_ID);
    });
    expect((await screen.findAllByText("Task Canonica")).length).toBeGreaterThan(0);
    expect(screen.getByText("Tarefa vinculada aberta sem criar duplicata.")).toBeInTheDocument();
    expect(workQueueService.executeItem).not.toHaveBeenCalled();
  });

  it("WQ runner trata 404 de tarefa canonica como recuperavel", async () => {
    vi.mocked(workQueueService.listItems).mockResolvedValue(
      makeEnvelope({ items: [makeItem({ canonical_task_id: TASK_CANONICAL_ID, primary_action_label: "Criar tarefa" })] }),
    );
    vi.mocked(workQueueService.getItem).mockRejectedValue({ response: { status: 404 } });

    renderRunner();

    expect((await screen.findAllByText("Ana Sintetica")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Continuar tarefa" }));

    expect(await screen.findByText("Tarefa vinculada indisponivel.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Atualizar fila" })).toBeInTheDocument();
    expect(workQueueService.executeItem).not.toHaveBeenCalled();
  });

  it("WQ runner limpa override canonico ao navegar para outra pagina", async () => {
    const recommendation = makeItem({
      source_id: "rec-canonical-page",
      canonical_task_id: TASK_CANONICAL_ID,
      primary_action_label: "Criar tarefa",
    });
    const task = makeItem({
      source_type: "task",
      source_id: TASK_CANONICAL_ID,
      canonical_task_id: TASK_CANONICAL_ID,
      subject_name: "Task Canonica Pagina Um",
      primary_action_label: "Retomar task existente",
    });
    vi.mocked(workQueueService.listItems).mockImplementation(async (params) =>
      makeEnvelope({
        items: [
          params?.page === 2
            ? makeItem({ source_id: "rec-page-2", subject_name: "Pagina Dois Depois Canonica" })
            : recommendation,
        ],
        total: 60,
        page: params?.page ?? 1,
        page_size: 25,
        state_counts: { do_now: 60, awaiting_outcome: 0, done: 0 },
      }),
    );
    vi.mocked(workQueueService.getItem).mockResolvedValue(task);

    renderRunner();

    expect((await screen.findAllByText("Ana Sintetica")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Continuar tarefa" }));
    expect((await screen.findAllByText("Task Canonica Pagina Um")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Proximo" }));

    expect((await screen.findAllByText("Pagina Dois Depois Canonica")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Pagina Dois Depois Canonica .*Criar tarefa/i })).toHaveFocus();
    });
    expect(screen.queryByText("Task Canonica Pagina Um")).not.toBeInTheDocument();
  });

  it("WQ runner mostra frescor, responsavel e lacunas sem bloquear quando freshness_blocking=false", async () => {
    vi.mocked(workQueueService.listItems).mockResolvedValue(
      makeEnvelope({
        items: [
          makeItem({
            freshness_state: "stale",
            freshness_blocking: false,
            readiness_missing_fields: ["signal", "due_at"],
            signal_value: null,
            priority_state: "unknown",
            assigned_to_name: "Dona Operacional",
            assigned_to_role: "manager",
          }),
        ],
      }),
    );

    renderRunner();

    expect(await screen.findByText("Dados desatualizados")).toBeInTheDocument();
    expect(screen.getByText("Responsavel: Dona Operacional (manager)")).toBeInTheDocument();
    expect(screen.getByText("Lacunas: signal, due_at")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /comecar execucao/i })).toBeEnabled();
  });

  it("WQ runner usa visible_from do snooze, remove o card e anuncia o retorno canonico", async () => {
    const first = makeItem({
      source_type: "task",
      source_id: "task-1",
      canonical_task_id: "task-1",
      subject_name: "Ana Snooze",
      primary_action_label: "Ligar",
    });
    const second = makeItem({
      source_type: "task",
      source_id: "task-2",
      canonical_task_id: "task-2",
      subject_name: "Bruno Proximo",
      primary_action_label: "Enviar WhatsApp",
    });
    vi.mocked(workQueueService.listItems).mockResolvedValue(makeEnvelope({ items: [first, second], total: 2, state_counts: { do_now: 2, awaiting_outcome: 0, done: 0 } }));
    vi.mocked(workQueueService.updateOutcome).mockResolvedValue(
      makeResult({
        ...first,
        state: "do_now",
        visible_from: "2026-07-14T09:00:00-03:00",
      } as WorkQueueItem),
    );

    renderRunner();

    expect((await screen.findAllByText("Ana Snooze")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Amanha" }));

    await waitFor(() => {
      expect(workQueueService.updateOutcome).toHaveBeenCalledWith("task", "task-1", expect.objectContaining({ outcome: "postponed", snooze_preset: "tomorrow" }));
    });
    expect((await screen.findAllByText("Bruno Proximo")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Bruno Proximo .*Enviar WhatsApp/i })).toHaveFocus();
    });
    expect(screen.queryByRole("button", { name: /Ana Snooze .*Ligar/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Retorna em 14\/07\/2026/)).toBeInTheDocument();
  });

  it("WQ runner remove card quando no_response volta com visible_from canonico", async () => {
    const first = makeItem({
      source_type: "task",
      source_id: "task-no-response",
      canonical_task_id: "task-no-response",
      subject_name: "Ana Sem Resposta",
      primary_action_label: "Ligar",
    });
    const second = makeItem({
      source_type: "task",
      source_id: "task-next",
      canonical_task_id: "task-next",
      subject_name: "Bruno Continua",
      primary_action_label: "Enviar WhatsApp",
    });
    vi.mocked(workQueueService.listItems).mockResolvedValue(
      makeEnvelope({ items: [first, second], total: 2, state_counts: { do_now: 2, awaiting_outcome: 0, done: 0 } }),
    );
    vi.mocked(workQueueService.updateOutcome).mockResolvedValue(
      makeResult({
        ...first,
        state: "do_now",
        visible_from: "2026-07-14T09:00:00-03:00",
      } as WorkQueueItem),
    );

    renderRunner();

    expect((await screen.findAllByText("Ana Sem Resposta")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Nao atendeu" }));

    await waitFor(() => {
      expect(workQueueService.updateOutcome).toHaveBeenCalledWith(
        "task",
        "task-no-response",
        expect.objectContaining({ outcome: "no_response", snooze_preset: "tomorrow" }),
      );
    });
    expect((await screen.findAllByText("Bruno Continua")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Bruno Continua .*Enviar WhatsApp/i })).toHaveFocus();
    });
    expect(screen.queryByRole("button", { name: /Ana Sem Resposta .*Ligar/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Retorna em 14\/07\/2026/)).toBeInTheDocument();
  });

  it("WQ runner remove recommendation original ao adiar task aberta via canonical_task_id", async () => {
    const recommendation = makeItem({
      source_id: "rec-linked-task",
      canonical_task_id: TASK_CANONICAL_ID,
      subject_name: "Ana Recommendation",
      primary_action_label: "Criar tarefa",
    });
    const nextRecommendation = makeItem({
      source_id: "rec-next-after-linked-task",
      subject_name: "Bruno Depois Canonica",
      primary_action_label: "Enviar WhatsApp",
    });
    const task = makeItem({
      source_type: "task",
      source_id: TASK_CANONICAL_ID,
      canonical_task_id: TASK_CANONICAL_ID,
      subject_name: "Task Canonica Adiavel",
      primary_action_label: "Ligar",
    });
    vi.mocked(workQueueService.listItems).mockResolvedValue(
      makeEnvelope({ items: [recommendation, nextRecommendation], total: 2, state_counts: { do_now: 2, awaiting_outcome: 0, done: 0 } }),
    );
    vi.mocked(workQueueService.getItem).mockResolvedValue(task);
    vi.mocked(workQueueService.updateOutcome).mockResolvedValue(
      makeResult({
        ...task,
        visible_from: "2026-07-14T09:00:00-03:00",
      } as WorkQueueItem),
    );

    renderRunner();

    expect((await screen.findAllByText("Ana Recommendation")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Continuar tarefa" }));
    expect((await screen.findAllByText("Task Canonica Adiavel")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Amanha" }));

    await waitFor(() => {
      expect(workQueueService.updateOutcome).toHaveBeenCalledWith(
        "task",
        TASK_CANONICAL_ID,
        expect.objectContaining({ outcome: "postponed", snooze_preset: "tomorrow" }),
      );
    });
    expect((await screen.findAllByText("Bruno Depois Canonica")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Bruno Depois Canonica .*Enviar WhatsApp/i })).toHaveFocus();
    });
    expect(screen.queryByRole("button", { name: /Ana Recommendation .*Criar tarefa/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Task Canonica Adiavel")).not.toBeInTheDocument();
  });
});
