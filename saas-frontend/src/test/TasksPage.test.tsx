import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "../pages/tasks/TasksPage";
import { memberService } from "../services/memberService";
import { taskService } from "../services/taskService";
import { userService } from "../services/userService";
import type { Member, Task } from "../types";

vi.mock("../services/taskService", () => ({
  taskService: {
    listTasks: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    createTask: vi.fn(),
  },
}));

vi.mock("../services/memberService", () => ({
  memberService: {
    listMembers: vi.fn(),
  },
}));

vi.mock("../services/userService", () => ({
  userService: {
    listUsers: vi.fn(),
  },
}));

const sampleMember: Member = {
  id: "member-1",
  full_name: "Ana Silva",
  email: "ana@teste.com",
  phone: null,
  status: "active",
  plan_name: "Plano Mensal",
  monthly_fee: 199,
  join_date: "2026-03-01",
  preferred_shift: null,
  nps_last_score: 9,
  loyalty_months: 1,
  risk_score: 55,
  risk_level: "yellow",
  last_checkin_at: "2026-03-10T10:00:00Z",
  extra_data: {},
  suggested_action: null,
  onboarding_status: "active",
  onboarding_score: 60,
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-10T00:00:00Z",
};

const sampleTask: Task = {
  id: "task-1",
  title: "Ligar para Ana Silva",
  description: "Automacao de retencao (7d) para aluno inativo.",
  member_id: "member-1",
  lead_id: null,
  assigned_to_user_id: null,
  member_name: "Ana Silva",
  lead_name: null,
  priority: "high",
  status: "todo",
  kanban_column: "todo",
  due_date: null,
  completed_at: null,
  suggested_message: "Oi Ana, notamos sua ausencia e queremos ajudar.",
  extra_data: { source: "onboarding", plan_type: "mensal" },
  created_at: "2026-03-10T00:00:00Z",
  updated_at: "2026-03-10T00:00:00Z",
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
        <TasksPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TasksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(taskService.listTasks).mockResolvedValue({
      items: [sampleTask],
      total: 1,
      page: 1,
      page_size: 50,
    });
    vi.mocked(memberService.listMembers).mockResolvedValue({
      items: [sampleMember],
      total: 1,
      page: 1,
      page_size: 20,
    });
    vi.mocked(userService.listUsers).mockResolvedValue([]);
  });

  it("renders key labels without mojibake", async () => {
    renderPage();

    expect(await screen.findByRole("button", { name: "Mostrar concluidas" })).toBeInTheDocument();
    expect(screen.getByText(/Operacao diaria e onboarding no mesmo modulo, organizados em visoes separadas\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fila operacional" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Onboarding" })).toBeInTheDocument();
    expect(screen.getByText("Mensagem sugerida")).toBeInTheDocument();
    expect(document.body.textContent ?? "").not.toMatch(/[Ã�]/);
  });
});
