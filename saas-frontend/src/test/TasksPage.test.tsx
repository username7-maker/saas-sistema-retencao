import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "../pages/tasks/TasksPage";
import { memberService } from "../services/memberService";
import { taskService } from "../services/taskService";
import { userService } from "../services/userService";
import { workQueueService } from "../services/workQueueService";
import type { Member, Task } from "../types";

let currentUserMock = { id: "user-1", full_name: "Julia Operacoes", work_shift: null as "morning" | "afternoon" | "evening" | null };

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: currentUserMock,
  }),
}));

vi.mock("../services/taskService", () => ({
  taskService: {
    listTasks: vi.fn(),
    listAllTasks: vi.fn(),
    getAssistant: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    createTask: vi.fn(),
  },
}));

vi.mock("../services/memberService", () => ({
  memberService: {
    listMemberIndex: vi.fn(),
    getOnboardingScore: vi.fn(),
    getOnboardingScoreboard: vi.fn(),
  },
}));

vi.mock("../services/userService", () => ({
  userService: {
    listUsers: vi.fn(),
  },
}));

vi.mock("../services/workQueueService", () => ({
  workQueueService: {
    listItems: vi.fn(),
    getItem: vi.fn(),
    executeItem: vi.fn(),
    updateOutcome: vi.fn(),
  },
}));

let members: Member[] = [];
let tasks: Task[] = [];

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
        <TasksPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function openCompleteList() {
  fireEvent.click(await screen.findByRole("button", { name: "Lista completa" }));
  return screen.findByText("Precisa de atencao agora");
}

describe("TasksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUserMock = { id: "user-1", full_name: "Julia Operacoes", work_shift: null };

    const now = new Date();
    const isoAtOffset = (days: number) => new Date(now.getTime() + days * 86_400_000).toISOString();
    const dateAtOffset = (days: number) => isoAtOffset(days).slice(0, 10);
    const isoTodayMorning = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 9, 0, 0),
    ).toISOString();

    members = [
      {
        id: "member-1",
        full_name: "Ana Silva",
        email: "ana@teste.com",
        phone: "11999990001",
        status: "active",
        plan_name: "Plano Mensal",
        monthly_fee: 199,
        join_date: dateAtOffset(-19),
        preferred_shift: "morning",
        nps_last_score: 9,
        loyalty_months: 1,
        risk_score: 82,
        risk_level: "red",
        last_checkin_at: isoAtOffset(-10),
        extra_data: {},
        suggested_action: null,
        onboarding_status: "at_risk",
        onboarding_score: 32,
        created_at: isoAtOffset(-19),
        updated_at: isoAtOffset(-10),
      },
      {
        id: "member-2",
        full_name: "Bruno Lima",
        email: "bruno@teste.com",
        phone: "11988887777",
        status: "active",
        plan_name: "Plano Anual",
        monthly_fee: 249,
        join_date: dateAtOffset(-15),
        preferred_shift: "evening",
        nps_last_score: 8,
        loyalty_months: 1,
        risk_score: 41,
        risk_level: "yellow",
        last_checkin_at: isoAtOffset(-3),
        extra_data: {},
        suggested_action: null,
        onboarding_status: "active",
        onboarding_score: 61,
        created_at: isoAtOffset(-15),
        updated_at: isoAtOffset(-3),
      },
      {
        id: "member-3",
        full_name: "Andre Luis Da Silva",
        email: "andre@teste.com",
        phone: null,
        status: "active",
        plan_name: "Plano Semestral",
        monthly_fee: 219,
        join_date: dateAtOffset(-33),
        preferred_shift: "afternoon",
        nps_last_score: 7,
        loyalty_months: 1,
        risk_score: 38,
        risk_level: "yellow",
        last_checkin_at: isoAtOffset(-2),
        extra_data: {},
        suggested_action: null,
        onboarding_status: "active",
        onboarding_score: 42,
        created_at: isoAtOffset(-33),
        updated_at: isoAtOffset(-2),
      },
      {
        id: "member-4",
        full_name: "Carla Freitas",
        email: "carla@teste.com",
        phone: "11970001111",
        status: "active",
        plan_name: "Plano Mensal Light",
        monthly_fee: 159,
        join_date: dateAtOffset(-45),
        preferred_shift: "morning",
        nps_last_score: 10,
        loyalty_months: 2,
        risk_score: 18,
        risk_level: "green",
        last_checkin_at: isoAtOffset(-1),
        extra_data: {},
        suggested_action: null,
        onboarding_status: "completed",
        onboarding_score: 84,
        created_at: isoAtOffset(-45),
        updated_at: isoAtOffset(-1),
      },
    ];

    tasks = [
      {
        id: "task-1",
        title: "Resolver atraso da Ana",
        description: "Contato humano por risco alto no onboarding.",
        member_id: "member-1",
        lead_id: null,
        assigned_to_user_id: "user-1",
        member_name: "Ana Silva",
        lead_name: null,
        preferred_shift: "morning",
        priority: "urgent",
        status: "todo",
        kanban_column: "todo",
        due_date: isoAtOffset(-1),
        completed_at: null,
        suggested_message: "Oi Ana, queremos entender como te ajudar a voltar ao ritmo.",
        extra_data: { source: "onboarding", plan_type: "mensal", day_offset: 1 },
        created_at: isoAtOffset(-8),
        updated_at: isoAtOffset(-8),
      },
      {
        id: "task-2",
        title: "Enviar follow-up para Bruno",
        description: "Confirmar agenda da semana.",
        member_id: "member-2",
        lead_id: null,
        assigned_to_user_id: "user-2",
        member_name: "Bruno Lima",
        lead_name: null,
        preferred_shift: "evening",
        priority: "high",
        status: "doing",
        kanban_column: "doing",
        due_date: isoAtOffset(0),
        completed_at: null,
        suggested_message: null,
        extra_data: { source: "plan_followup", plan_type: "anual" },
        created_at: isoAtOffset(-6),
        updated_at: isoAtOffset(0),
      },
      {
        id: "task-3",
        title: "Revisar proposta de retorno",
        description: null,
        member_id: null,
        lead_id: "lead-1",
        assigned_to_user_id: null,
        member_name: null,
        lead_name: "Lead Carlos",
        preferred_shift: null,
        priority: "medium",
        status: "todo",
        kanban_column: "todo",
        due_date: isoAtOffset(4),
        completed_at: null,
        suggested_message: null,
        extra_data: { source: "manual" },
        created_at: isoAtOffset(-4),
        updated_at: isoAtOffset(-4),
      },
      {
        id: "task-4",
        title: "Registrar retorno concluido",
        description: null,
        member_id: "member-2",
        lead_id: null,
        assigned_to_user_id: "user-1",
        member_name: "Bruno Lima",
        lead_name: null,
        preferred_shift: "evening",
        priority: "low",
        status: "done",
        kanban_column: "done",
        due_date: null,
        completed_at: isoTodayMorning,
        suggested_message: null,
        extra_data: { source: "automation" },
        created_at: isoAtOffset(-10),
        updated_at: isoTodayMorning,
      },
      {
        id: "task-5",
        title: "Confirmar frequencia da Carla",
        description: "Contato leve de acompanhamento.",
        member_id: "member-4",
        lead_id: null,
        assigned_to_user_id: "user-2",
        member_name: "Carla Freitas",
        lead_name: null,
        preferred_shift: "morning",
        priority: "medium",
        status: "todo",
        kanban_column: "todo",
        due_date: isoAtOffset(5),
        completed_at: null,
        suggested_message: null,
        extra_data: { source: "manual", plan_type: "mensal" },
        created_at: isoAtOffset(-2),
        updated_at: isoAtOffset(-1),
      },
      {
        id: "task-6",
        title: "Handoff D7 com Bruno",
        description: "Checar adesao e proximo passo da jornada.",
        member_id: "member-2",
        lead_id: null,
        assigned_to_user_id: "user-2",
        member_name: "Bruno Lima",
        lead_name: null,
        preferred_shift: "evening",
        priority: "medium",
        status: "todo",
        kanban_column: "todo",
        due_date: isoAtOffset(2),
        completed_at: null,
        suggested_message: null,
        extra_data: { source: "onboarding", plan_type: "anual", day_offset: 7, onboarding_phase: "handoff" },
        created_at: isoAtOffset(-3),
        updated_at: isoAtOffset(-1),
      },
    ];

    vi.mocked(taskService.listAllTasks).mockResolvedValue({
      items: tasks,
      total: tasks.length,
      page: 1,
      page_size: 50,
    });
    vi.mocked(taskService.getAssistant).mockResolvedValue({
      summary: "Ana esta em onboarding de risco alto.",
      why_it_matters: "Sem contato rapido, ela pode esfriar antes do D30.",
      next_best_action: "Abrir o perfil e fazer o contato hoje.",
      suggested_message: "Oi Ana, quero te ajudar a voltar ao ritmo desta semana.",
      evidence: ["1 check-in nos ultimos 17 dias", "Primeira avaliacao pendente"],
      provider: "system",
      mode: "rule_based",
      fallback_used: false,
      manual_required: true,
      confidence_label: "Prioridade imediata",
      recommended_channel: "WhatsApp",
      cta_target: "/assessments/members/member-1?tab=acoes",
      cta_label: "Abrir perfil",
    });
    vi.mocked(taskService.updateTask).mockResolvedValue(tasks[0]);
    vi.mocked(taskService.deleteTask).mockResolvedValue();
    vi.mocked(taskService.createTask).mockResolvedValue(tasks[0]);

    vi.mocked(memberService.listMemberIndex).mockResolvedValue(members);
    vi.mocked(memberService.getOnboardingScoreboard).mockResolvedValue([
      { member_id: "member-1", score: 32, status: "at_risk" },
      { member_id: "member-2", score: 61, status: "active" },
    ]);
    vi.mocked(memberService.getOnboardingScore).mockResolvedValue({
      score: 32,
      status: "at_risk",
      factors: {
        checkin_frequency: 20,
        first_assessment: 0,
        task_completion: 35,
        consistency: 40,
        member_response: 0,
      },
      days_since_join: 17,
      checkin_count: 1,
      completed_tasks: 1,
      total_tasks: 3,
    });

    vi.mocked(userService.listUsers).mockResolvedValue([
      {
        id: "user-1",
        gym_id: "gym-1",
        full_name: "Julia Operacoes",
        email: "julia@teste.com",
        role: "manager",
        is_active: true,
        work_shift: null,
        created_at: "2026-03-01T00:00:00Z",
      },
      {
        id: "user-2",
        gym_id: "gym-1",
        full_name: "Carlos Time",
        email: "carlos@teste.com",
        role: "trainer",
        is_active: true,
        work_shift: "evening",
        created_at: "2026-03-01T00:00:00Z",
      },
    ]);

    vi.mocked(workQueueService.listItems).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    });
  });

  it("renders triage as the default operational view with fixed sections", async () => {
    renderPage();

    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.getByText("Acompanhamento de acoes e follow-ups pendentes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Modo execucao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lista completa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Onboarding" })).toBeInTheDocument();
    expect(await screen.findByText("Modo execucao operacional")).toBeInTheDocument();
    expect(screen.getByText("Fila unica de tasks e AI Inbox por turno. Comece a execucao, registre o resultado e avance sem abrir varias telas.")).toBeInTheDocument();
    expect(await screen.findByText("Nenhuma acao nessa fila")).toBeInTheDocument();
  });

  it("keeps the full operational list behind the advanced tab", async () => {
    renderPage();
    await openCompleteList();

    expect(await screen.findByText("Precisa de atencao agora")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Triage" })).toBeInTheDocument();
    expect(screen.getByText("Total visiveis")).toBeInTheDocument();
    expect(screen.getByText("Pendentes")).toBeInTheDocument();
    expect(screen.getByText("Vencidas")).toBeInTheDocument();
    expect(screen.getByText("Concluidas hoje")).toBeInTheDocument();
    expect(screen.getAllByText("Sem responsavel").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Atrasadas").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Hoje").length).toBeGreaterThan(0);
    expect(screen.getByText("Proximas 7 dias")).toBeInTheDocument();
  });

  it("does not duplicate triage tasks across sections and allows quick assign inline", async () => {
    renderPage();

    await openCompleteList();
    expect(screen.getByText("Lead: Lead Carlos")).toBeInTheDocument();
    expect(screen.getAllByText("Lead: Lead Carlos")).toHaveLength(1);
    expect(screen.getByText("Nenhuma task sem responsavel.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Assumir Revisar proposta de retorno" }));

    await waitFor(() => {
      expect(taskService.updateTask).toHaveBeenCalledWith("task-3", { assigned_to_user_id: "user-1" });
    });
  });

  it("filters by only mine and clears filters", async () => {
    renderPage();

    await openCompleteList();

    fireEvent.click(screen.getByRole("button", { name: "So minhas" }));

    await waitFor(() => {
      expect(screen.queryByText("Lead: Lead Carlos")).not.toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /Ana Silva .*Resolver atraso da Ana/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Bruno Lima .*Enviar follow-up para Bruno/i })).not.toBeInTheDocument();
    expect(screen.getByText("Limpar filtros")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Limpar filtros"));

    await waitFor(() => {
      expect(screen.getByText("Lead: Lead Carlos")).toBeInTheDocument();
    });
  });

  it("supports quick action and an enriched detail drawer", async () => {
    renderPage();

    await openCompleteList();

    fireEvent.click(screen.getByRole("button", { name: /Editar Resolver atraso da Ana/i }));

    expect(await screen.findByText("Detalhe da tarefa")).toBeInTheDocument();
    expect(await screen.findByText("Ana esta em onboarding de risco alto.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Resolver atraso da Ana")).toBeInTheDocument();
    expect(screen.getAllByText("Mensagem sugerida").length).toBeGreaterThan(0);
    expect(screen.getByText("Estado operacional")).toBeInTheDocument();
    expect(screen.getAllByText("Sistema").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Baseado em regras").length).toBeGreaterThan(0);
    expect(screen.getByText("A recomendacao e explicavel, mas a execucao continua supervisionada neste ciclo.")).toBeInTheDocument();
    expect(screen.getByText("Contato do aluno")).toBeInTheDocument();
    expect(screen.getByText("Risco atual")).toBeInTheDocument();
    expect(screen.getByText(/Score 82/i)).toBeInTheDocument();
    expect(screen.getByText("Ultimo check-in")).toBeInTheDocument();
    expect(screen.getAllByText("Turno Manha").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Ligar" })).toHaveAttribute("href", "tel:5511999990001");
    expect(screen.getByRole("link", { name: "WhatsApp" })).toHaveAttribute(
      "href",
      expect.stringContaining("https://wa.me/5511999990001?text="),
    );

    fireEvent.click(screen.getByRole("button", { name: /Iniciar Resolver atraso da Ana/i }));

    await waitFor(() => {
      expect(taskService.updateTask).toHaveBeenCalledWith("task-1", { status: "doing" });
    });
  }, 10000);

  it("keeps onboarding in a dedicated tab with journey buckets and the queue CTA", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Onboarding" }));

    expect(await screen.findByText("Onboarding preservado")).toBeInTheDocument();
    expect(screen.getByText("Intelligence de onboarding")).toBeInTheDocument();
    expect(screen.getByText("Jornada ativa do onboarding")).toBeInTheDocument();
    expect(screen.getByText("Pendentes")).toBeInTheDocument();
    expect(screen.getAllByText("Sem responsavel").length).toBeGreaterThan(0);
    expect(screen.getByText("D0 / D1")).toBeInTheDocument();
    expect(screen.getAllByText("D7").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Ver tasks de onboarding" }));

    expect(await screen.findByText("Precisa de atencao agora")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ana Silva .*Resolver atraso da Ana/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bruno Lima .*Handoff D7 com Bruno/i })).toBeInTheDocument();
    expect(screen.queryByText("Lead: Lead Carlos")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Carla Freitas .*Confirmar frequencia da Carla/i })).not.toBeInTheDocument();
  });

  it("uses the resolved onboarding score to render the detail severity", async () => {
    vi.mocked(memberService.getOnboardingScore).mockResolvedValueOnce({
      score: 72,
      status: "active",
      days_since_join: 6,
      factors: {
        checkin_frequency: 100,
        first_assessment: 0,
        task_completion: 0,
        consistency: 100,
        member_response: 0,
      },
      checkin_count: 3,
      completed_tasks: 0,
      total_tasks: 1,
      assistant: {
        summary: "Aluno com presenca forte, mas ainda sem avaliacao inicial.",
        next_best_action: "Agendar a primeira avaliacao e transformar a entrada em um plano claro.",
        why_it_matters: "A frequencia ja apareceu. Falta consolidar objetivo e plano para reduzir risco futuro.",
        suggested_message: "Oi Paulo, vamos marcar sua primeira avaliacao para ajustar meta, frequencia e plano de treino?",
        evidence: ["3 check-in(s) nos primeiros 6 dias", "0/1 tarefa(s) concluidas no onboarding", "Primeira avaliacao: 0%"],
        provider: "system",
        mode: "rule_based",
        fallback_used: false,
        manual_required: true,
        confidence_label: "Acompanhamento assistido",
        recommended_channel: "WhatsApp",
        cta_target: "/assessments/members/member-1?tab=acoes",
        cta_label: "Abrir avaliacao",
      },
    });

    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Onboarding" }));
    await screen.findByText("Intelligence de onboarding");
    fireEvent.click(screen.getByRole("button", { name: /Bruno Lima .*61/i }));

    expect((await screen.findAllByText("72")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Engajados")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Score alto e rotina estavel").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Bruno Lima .*72/i })).toBeInTheDocument();
    const engagedCards = screen.getAllByText("Engajados");
    const summaryCard = engagedCards
      .map((label) => label.closest("button"))
      .find((node): node is HTMLButtonElement => Boolean(node));
    expect(summaryCard).toBeTruthy();
    expect(within(summaryCard!).getByText("1")).toBeInTheDocument();
  });

  it("applies the logged-in shift as the default task scope and allows turning it off", async () => {
    currentUserMock = { id: "user-1", full_name: "Julia Operacoes", work_shift: "morning" };

    renderPage();

    await openCompleteList();
    expect(screen.getByRole("button", { name: "Meu turno: Manha" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Bruno Lima .*Enviar follow-up para Bruno/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ana Silva .*Resolver atraso da Ana/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Meu turno: Manha" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Bruno Lima .*Enviar follow-up para Bruno/i })).toBeInTheDocument();
    });
  });

  it("opens the create task drawer from the page header", async () => {
    renderPage();

    await screen.findByText("Modo execucao operacional");
    fireEvent.click(screen.getByRole("button", { name: /\+ Nova Tarefa/i }));

    expect(await screen.findByText("Nova tarefa")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ex.: Ligar para Ana Silva")).toBeInTheDocument();
  });

  it("shows a standardized empty state when there are no tasks", async () => {
    vi.mocked(taskService.listAllTasks).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
    });

    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Lista completa" }));

    expect(await screen.findByText("Nenhuma tarefa cadastrada")).toBeInTheDocument();
    expect(screen.getByText("Crie a primeira task para comecar a organizar os follow-ups do time.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nova tarefa" })).toBeInTheDocument();
  });
});
