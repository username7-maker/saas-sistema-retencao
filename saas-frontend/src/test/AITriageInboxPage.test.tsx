import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AITriageInboxPage from "../pages/ai/AITriageInboxPage";
import { workQueueService } from "../services/workQueueService";
import type { WorkQueueActionResult, WorkQueueItem } from "../types";

let currentUserMock = {
  id: "user-1",
  full_name: "Julia Operacoes",
  role: "manager" as const,
  work_shift: null as "morning" | "afternoon" | "evening" | null,
};

vi.mock("../services/workQueueService", () => ({
  workQueueService: {
    listItems: vi.fn(),
    getItem: vi.fn(),
    executeItem: vi.fn(),
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

function makeItem(overrides?: Partial<WorkQueueItem>): WorkQueueItem {
  return {
    source_type: "ai_triage",
    source_id: "rec-1",
    subject_name: "Ana Silva",
    member_id: "member-1",
    lead_id: null,
    subject_phone: "+5554999990000",
    domain: "retention",
    severity: "medium",
    preferred_shift: "morning",
    reason: "16 dias sem check-in e forecast baixo.",
    primary_action_label: "Preparar WhatsApp",
    primary_action_type: "prepare_outbound_message",
    suggested_message: "Oi Ana, vamos retomar sua rotina?",
    requires_confirmation: false,
    state: "do_now",
    due_at: null,
    assigned_to_user_id: "user-1",
    context_path: "/assessments/members/member-1?tab=acoes",
    outcome_state: "pending",
    ...overrides,
  };
}

function makeResult(item: WorkQueueItem): WorkQueueActionResult {
  return {
    item,
    detail: "Acao preparada.",
    prepared_message: item.suggested_message,
    context_path: item.context_path,
    metadata: {},
  };
}

function mockQueue(doNowItems: WorkQueueItem[], awaitingItems: WorkQueueItem[] = []) {
  vi.mocked(workQueueService.listItems).mockImplementation(async (params) => {
    const state = params?.state ?? "do_now";
    const items = state === "awaiting_outcome" ? awaitingItems : state === "all" ? [...doNowItems, ...awaitingItems] : doNowItems;
    return { items, total: items.length, page: 1, page_size: 25 };
  });
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
    currentUserMock = { id: "user-1", full_name: "Julia Operacoes", role: "manager", work_shift: null };
  });

  it("executes a normal inbox item from the unified queue", async () => {
    const item = makeItem();
    mockQueue([item]);
    vi.mocked(workQueueService.executeItem).mockResolvedValue(makeResult({ ...item, state: "awaiting_outcome" }));

    renderPage();

    expect(await screen.findByText("Execucao da AI Inbox")).toBeInTheDocument();
    expect((await screen.findAllByText("Ana Silva")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByPlaceholderText("Observacao opcional para esta acao"), {
      target: { value: "Pode seguir agora." },
    });
    fireEvent.click(screen.getByRole("button", { name: /comecar execucao/i }));

    await waitFor(() => {
      expect(workQueueService.executeItem).toHaveBeenCalledWith("ai_triage", "rec-1", {
        auto_approve: true,
        confirm_approval: false,
        operator_note: "Pode seguir agora.",
      });
    });
  });

  it("requires a short confirmation for critical inbox items", async () => {
    const item = makeItem({ severity: "critical", requires_confirmation: true, primary_action_label: "Criar tarefa" });
    mockQueue([item]);
    vi.mocked(workQueueService.executeItem).mockResolvedValue(makeResult({ ...item, state: "awaiting_outcome" }));

    renderPage();

    expect((await screen.findAllByText("Ana Silva")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /comecar execucao/i }));
    expect(await screen.findByText("Confirmar preparacao?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /confirmar e comecar/i }));

    await waitFor(() => {
      expect(workQueueService.executeItem).toHaveBeenCalledWith("ai_triage", "rec-1", {
        auto_approve: false,
        confirm_approval: true,
        operator_note: null,
      });
    });
  });

  it("registers outcome from awaiting result view", async () => {
    const awaiting = makeItem({ state: "awaiting_outcome", primary_action_label: "Registrar resultado" });
    mockQueue([], [awaiting]);
    vi.mocked(workQueueService.updateOutcome).mockResolvedValue(makeResult({ ...awaiting, state: "done", outcome_state: "positive" }));

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /aguardando resultado \(1\)/i }));
    expect(await screen.findByText("Acao ja preparada. Registre o resultado assim que houver retorno.")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Observacao opcional para esta acao"), {
      target: { value: "Aluno respondeu." },
    });
    fireEvent.click(screen.getByRole("button", { name: /respondeu/i }));

    await waitFor(() => {
      expect(workQueueService.updateOutcome).toHaveBeenCalledWith("ai_triage", "rec-1", {
        outcome: "responded",
        note: "Aluno respondeu.",
      });
    });
  });

  it("renders empty and degraded states", async () => {
    mockQueue([]);
    renderPage();
    expect(await screen.findByText("Nenhuma acao nessa fila")).toBeInTheDocument();
  });

  it("keeps my shift as the default filter and lets managers open all shifts", async () => {
    currentUserMock = { id: "user-1", full_name: "Julia Operacoes", role: "manager", work_shift: "morning" };
    mockQueue([makeItem()]);

    renderPage();

    expect(await screen.findByRole("button", { name: "Meu turno" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Todos os turnos" }));

    await waitFor(() => {
      expect(workQueueService.listItems).toHaveBeenCalledWith(
        expect.objectContaining({ source: "ai_triage", shift: "all", state: "do_now" }),
      );
    });
  });
});
