import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MethodOsPage } from "../pages/method/MethodOsPage";
import { methodOsService } from "../services/methodOsService";
import type { MethodClientProfile, MethodDashboard, MethodOperationalTask, MethodPerson, MethodSegment } from "../types";

vi.mock("../services/methodOsService", () => ({
  methodOsService: {
    listSegments: vi.fn(),
    getClientProfile: vi.fn(),
    updateClientConfig: vi.fn(),
    copyPlaybookToClient: vi.fn(),
    listPeople: vi.fn(),
    createPerson: vi.fn(),
    createEvent: vi.fn(),
    generateTaskFromEvent: vi.fn(),
    listTasks: vi.fn(),
    updateTaskMessage: vi.fn(),
    createAction: vi.fn(),
    createOutcome: vi.fn(),
    getDashboard: vi.fn(),
    generateWeeklyReport: vi.fn(),
  },
}));

const segment: MethodSegment = {
  id: "segment-1",
  slug: "clinica",
  name: "Clinica",
  description: "Clinica",
  default_entry_pillar: "post_sale",
};

const profile: MethodClientProfile = {
  client: {
    cordex_client_id: "client-1",
    name: "Cordex Demo",
    slug: "cordex-demo",
    is_active: true,
    segment_id: segment.id,
    status: "active",
    city: "Sao Paulo",
    state: "SP",
    main_contact_name: null,
    main_contact_phone: null,
    main_contact_email: null,
  },
  config: {
    id: "config-1",
    cordex_client_id: "client-1",
    segment_id: segment.id,
    active_pillars: { acquisition: true, sales: true, post_sale: true },
    entry_pillar: "post_sale",
    toolkit: {},
    baseline: {},
    success_criteria: {},
    cadence: {},
  },
  segment,
  playbook: {
    id: "playbook-1",
    segment_id: segment.id,
    channels: ["WhatsApp", "telefone"],
    qualification_questions: ["Qual necessidade?"],
    risk_opportunity_signals: ["no_return_scheduled"],
    message_templates: { retorno: "Oi {nome}" },
    success_metrics: ["retorno"],
    segment,
  },
};

const dashboard: MethodDashboard = {
  cordex_client_id: "client-1",
  generated_at: "2026-06-03T12:00:00Z",
  open_tasks: 2,
  overdue_tasks: 1,
  completed_7d: 3,
  people_total: 4,
  leads_total: 2,
  customers_total: 2,
  opportunities: 1,
  closed_sales: 1,
  risk_customers: 1,
  recovered_customers: 1,
  by_pillar: { acquisition: 0, sales: 1, post_sale: 1 },
  by_priority: { low: 0, medium: 1, high: 1, critical: 0 },
  bottlenecks: ["1 tarefa vencida"],
  recommendations: ["Resolver vencidas"],
};

const person: MethodPerson = {
  id: "person-1",
  cordex_client_id: "client-1",
  external_id: null,
  name: "Maria Silva",
  phone: "11 99999-0001",
  email: null,
  person_type: "lead",
  status: "active",
  source_channel: "whatsapp",
  metadata: {},
};

function task(overrides?: Partial<MethodOperationalTask>): MethodOperationalTask {
  return {
    id: "task-1",
    cordex_client_id: "client-1",
    person_id: "person-1",
    person_name: "Maria Silva",
    person_phone: "11 99999-0001",
    event_id: "event-1",
    pillar: "sales",
    task_type: "follow_up",
    title: "Fazer follow-up comercial",
    description: "Retomar conversa",
    assigned_role: "comercial",
    assigned_to: null,
    priority: "high",
    status: "open",
    due_date: "2026-06-03T14:00:00Z",
    suggested_message: "Oi Maria, podemos falar hoje?",
    wa_me_link: "https://wa.me/5511999990001?text=Oi%20Maria",
    dismissal_reason: null,
    completed_at: null,
    dismissed_at: null,
    requires_human_approval: true,
    ai_metadata: {},
    metadata: {},
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
      <MethodOsPage />
    </QueryClientProvider>,
  );
}

describe("MethodOsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "open").mockImplementation(() => null);
    vi.mocked(methodOsService.listSegments).mockResolvedValue([segment]);
    vi.mocked(methodOsService.getClientProfile).mockResolvedValue(profile);
    vi.mocked(methodOsService.getDashboard).mockResolvedValue(dashboard);
    vi.mocked(methodOsService.listPeople).mockResolvedValue([person]);
    vi.mocked(methodOsService.listTasks).mockResolvedValue([task()]);
    vi.mocked(methodOsService.updateTaskMessage).mockResolvedValue(task({ suggested_message: "Mensagem revisada", wa_me_link: "https://wa.me/5511999990001?text=Mensagem%20revisada" }));
    vi.mocked(methodOsService.createAction).mockResolvedValue({
      id: "action-1",
      cordex_client_id: "client-1",
      person_id: "person-1",
      task_id: "task-1",
      action_type: "whatsapp",
      action_summary: "Contato feito",
      result: "responded",
      notes: null,
      created_by: "Owner",
      created_at: "2026-06-03T12:00:00Z",
    });
    vi.mocked(methodOsService.createOutcome).mockResolvedValue({
      id: "outcome-1",
      cordex_client_id: "client-1",
      person_id: "person-1",
      task_id: "task-1",
      action_id: "action-1",
      outcome_type: "closed_sale",
      value_numeric: null,
      value_text: null,
      measured_at: "2026-06-03T12:00:00Z",
      created_at: "2026-06-03T12:00:00Z",
    });
    vi.mocked(methodOsService.generateWeeklyReport).mockResolvedValue({
      report_id: "report-1",
      cordex_client_id: "client-1",
      report_type: "weekly",
      period_start: "2026-05-27T12:00:00Z",
      period_end: "2026-06-03T12:00:00Z",
      summary: "Resumo",
      markdown: "# Relatorio semanal Cordex Method OS\n\n- Tarefas criadas: 2",
      metrics: {},
      bottlenecks: [],
      recommendations: [],
      requires_human_review: true,
    });
  });

  it("renders dashboard, config, task and report sections", async () => {
    renderPage();

    expect(await screen.findByText("Cordex Demo")).toBeInTheDocument();
    expect(screen.getByText("Tarefas de hoje")).toBeInTheDocument();
    expect(screen.getAllByText("Fazer follow-up comercial").length).toBeGreaterThan(0);
    expect(screen.getByText("Relatorio semanal")).toBeInTheDocument();
  });

  it("allows editing the suggested message before opening WhatsApp", async () => {
    renderPage();

    const message = await screen.findByDisplayValue("Oi Maria, podemos falar hoje?");
    fireEvent.change(message, { target: { value: "Mensagem revisada" } });
    fireEvent.click(screen.getByRole("button", { name: /Abrir WhatsApp/i }));

    await waitFor(() => {
      expect(methodOsService.updateTaskMessage).toHaveBeenCalledWith("task-1", "Mensagem revisada");
      expect(window.open).toHaveBeenCalledWith("https://wa.me/5511999990001?text=Mensagem%20revisada", "_blank", "noopener,noreferrer");
    });
  });

  it("disables WhatsApp for invalid phones but still records action and outcome", async () => {
    vi.mocked(methodOsService.listTasks).mockResolvedValue([
      task({ id: "task-invalid", person_phone: "99999-0001", wa_me_link: null }),
    ]);
    renderPage();

    await screen.findByText("Cordex Demo");
    expect(screen.getAllByText("Fazer follow-up comercial").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Abrir WhatsApp/i })).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("Resumo da acao humana"), { target: { value: "Contato por ligacao" } });
    fireEvent.change(screen.getByLabelText("Resultado medido"), { target: { value: "closed_sale" } });
    fireEvent.click(screen.getByRole("button", { name: /Registrar acao/i }));

    await waitFor(() => {
      expect(methodOsService.createAction).toHaveBeenCalledWith("task-invalid", expect.objectContaining({ action_summary: "Contato por ligacao" }));
      expect(methodOsService.createOutcome).toHaveBeenCalledWith(expect.objectContaining({ task_id: "task-invalid", outcome_type: "closed_sale" }));
    });
  });
});
