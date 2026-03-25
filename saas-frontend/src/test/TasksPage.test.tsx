import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "../pages/tasks/TasksPage";
import { memberService } from "../services/memberService";
import { taskService } from "../services/taskService";
import { userService } from "../services/userService";
import type { Member, Task } from "../types";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "user-1", full_name: "Julia Operacoes" },
  }),
}));

vi.mock("../services/taskService", () => ({
  taskService: {
    listTasks: vi.fn(),
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
  },
}));

vi.mock("../services/userService", () => ({
  userService: {
    listUsers: vi.fn(),
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

describe("TasksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

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
        preferred_shift: null,
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
        preferred_shift: null,
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
        full_name: "André Luis Da Silva",
        email: "andre@teste.com",
        phone: null,
        status: "active",
        plan_name: "Plano Semestral",
        monthly_fee: 219,
        join_date: dateAtOffset(-33),
        preferred_shift: null,
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
        priority: "urgent",
        status: "todo",
        kanban_column: "todo",
        due_date: isoAtOffset(-1),
        completed_at: null,
        suggested_message: "Oi Ana, queremos entender como te ajudar a voltar ao ritmo.",
        extra_data: { source: "onboarding", plan_type: "mensal" },
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
    ];

    vi.mocked(taskService.listTasks).mockResolvedValue({
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
      confidence_label: "Prioridade imediata",
      recommended_channel: "WhatsApp",
      cta_target: "/assessments/members/member-1?tab=acoes",
      cta_label: "Abrir perfil",
    });
    vi.mocked(taskService.updateTask).mockResolvedValue(tasks[0]);
    vi.mocked(taskService.deleteTask).mockResolvedValue();
    vi.mocked(taskService.createTask).mockResolvedValue(tasks[0]);

    vi.mocked(memberService.listMemberIndex).mockResolvedValue(members);
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
        created_at: "2026-03-01T00:00:00Z",
      },
      {
        id: "user-2",
        gym_id: "gym-1",
        full_name: "Carlos Time",
        email: "carlos@teste.com",
        role: "trainer",
        is_active: true,
        created_at: "2026-03-01T00:00:00Z",
      },
    ]);
  });

  it("renders operacao as default with cleaner hierarchy", async () => {
    renderPage();

    expect(screen.getByText("Tarefas")).toBeInTheDocument();
    expect(screen.getByText("Acompanhamento de acoes e follow-ups pendentes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Operacao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Onboarding" })).toBeInTheDocument();
    expect(await screen.findByText("Precisa de atencao agora")).toBeInTheDocument();
    expect(screen.getByText("Total visiveis")).toBeInTheDocument();
    expect(screen.getByText("Pendentes")).toBeInTheDocument();
    expect(screen.getByText("Vencidas")).toBeInTheDocument();
    expect(screen.getByText("Concluidas hoje")).toBeInTheDocument();
    expect(screen.getAllByText("Atrasadas").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Concluidas recentemente").length).toBeGreaterThan(0);
  });

  it("filters by only mine and clears filters", async () => {
    renderPage();

    await screen.findByText("Precisa de atencao agora");

    fireEvent.click(screen.getByRole("button", { name: "So minhas" }));

    await waitFor(() => {
      expect(screen.getByText("Limpar filtros")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Limpar filtros"));

    await waitFor(() => {
      expect(screen.queryByText("Limpar filtros")).not.toBeInTheDocument();
    });
  });

  it("supports quick action and detail drawer", async () => {
    renderPage();

    await screen.findByText("Precisa de atencao agora");

    fireEvent.click(screen.getAllByRole("button", { name: /Iniciar Resolver atraso da Ana/i })[0]);

    await waitFor(() => {
      expect(taskService.updateTask).toHaveBeenCalled();
    });
    expect(taskService.updateTask).toHaveBeenCalledWith("task-1", { status: "doing" });

    fireEvent.click(screen.getAllByRole("button", { name: /Editar Resolver atraso da Ana/i })[0]);

    expect(await screen.findByText("Detalhe da tarefa")).toBeInTheDocument();
    expect(await screen.findByText("Ana esta em onboarding de risco alto.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Resolver atraso da Ana")).toBeInTheDocument();
    expect(screen.getAllByText("Mensagem sugerida").length).toBeGreaterThan(0);
    expect(screen.getByText("Contato do aluno")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ligar" })).toHaveAttribute("href", "tel:5511999990001");
    expect(screen.getByRole("link", { name: "WhatsApp" })).toHaveAttribute(
      "href",
      expect.stringContaining("https://wa.me/5511999990001?text="),
    );
  }, 10000);

  it("keeps onboarding in a dedicated tab", async () => {
    renderPage();

    await screen.findByText("Precisa de atencao agora");
    fireEvent.click(screen.getByRole("button", { name: "Onboarding" }));

    expect(await screen.findByText("Onboarding preservado")).toBeInTheDocument();
    expect(screen.getByText("Intelligence de onboarding")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver tasks de onboarding" })).toBeInTheDocument();
    expect(screen.getByText("Onboarding ativo: 2")).toBeInTheDocument();
    expect(screen.queryByText("André Luis Da Silva")).not.toBeInTheDocument();
  });

  it("opens the create task drawer from the page header", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /\+ Nova Tarefa/i }));

    expect(await screen.findByText("Nova tarefa")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ex.: Ligar para Ana Silva")).toBeInTheDocument();
  });

  it("shows a standardized empty state when there are no tasks", async () => {
    vi.mocked(taskService.listTasks).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
    });

    renderPage();

    expect(await screen.findByText("Nenhuma tarefa cadastrada")).toBeInTheDocument();
    expect(screen.getByText("Crie a primeira task para comecar a organizar os follow-ups do time.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nova tarefa" })).toBeInTheDocument();
  });
});
