import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CrmPage } from "../pages/crm/CrmPage";
import { crmService } from "../services/crmService";
import type { Lead, PaginatedResponse } from "../types";

const authState = vi.hoisted(() => ({
  user: {
    id: "owner-1",
    full_name: "Owner Teste",
    role: "owner" as "owner" | "manager" | "receptionist" | "salesperson" | "trainer",
  },
}));

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: authState.user,
  }),
}));

vi.mock("../services/crmService", async () => {
  const actual = await vi.importActual<typeof import("../services/crmService")>("../services/crmService");
  return {
    ...actual,
    crmService: {
      ...actual.crmService,
      listLeads: vi.fn(),
      createLead: vi.fn(),
      updateLead: vi.fn(),
      appendLeadNote: vi.fn(),
      updateLeadStage: vi.fn(),
      deleteLead: vi.fn(),
    },
  };
});

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function makeLead(overrides: Partial<Lead> & Pick<Lead, "id" | "full_name" | "stage">): Lead {
  const now = new Date().toISOString();
  const { id, full_name, stage, ...rest } = overrides;
  return {
    id,
    full_name,
    email: `${overrides.id}@teste.com`,
    phone: "(11) 99999-9999",
    source: "Instagram",
    stage,
    estimated_value: 500,
    acquisition_cost: 0,
    owner_id: null,
    last_contact_at: null,
    converted_member_id: null,
    notes: [],
    lost_reason: null,
    created_at: now,
    updated_at: now,
    ...rest,
  };
}

const now = new Date();
const eightDaysAgo = new Date(now.getTime() - 8 * 24 * 60 * 60 * 1000).toISOString();
const oneDayAgo = new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000).toISOString();

const leads: Lead[] = [
  makeLead({
    id: "lead-1",
    full_name: "Ana Silva",
    stage: "new",
    source: "Instagram",
    estimated_value: 350,
    last_contact_at: null,
    notes: ["Lead frio, ainda sem contato."],
  }),
  makeLead({
    id: "lead-2",
    full_name: "Bruno Lima",
    stage: "proposal",
    source: "Google",
    estimated_value: 1200,
    last_contact_at: eightDaysAgo,
    notes: ["Precisa aprovar com a esposa."],
  }),
  makeLead({
    id: "lead-3",
    full_name: "Carla Souza",
    stage: "won",
    source: "Indicacao",
    estimated_value: 900,
    last_contact_at: oneDayAgo,
    updated_at: now.toISOString(),
  }),
];

const response: PaginatedResponse<Lead> = {
  items: leads,
  total: leads.length,
  page: 1,
  page_size: 200,
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
        <CrmPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CrmPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = { id: "owner-1", full_name: "Owner Teste", role: "owner" };
    vi.mocked(crmService.listLeads).mockResolvedValue(response);
    vi.mocked(crmService.createLead).mockResolvedValue(leads[0]);
    vi.mocked(crmService.updateLead).mockResolvedValue(leads[1]);
    vi.mocked(crmService.appendLeadNote).mockResolvedValue({
      ...leads[1],
      notes: [
        "Precisa aprovar com a esposa.",
        {
          type: "note",
          note: "Cliente pediu retorno na sexta.",
          created_at: new Date().toISOString(),
          author_name: "Owner Teste",
          author_role: "owner",
        },
      ],
    });
    vi.mocked(crmService.updateLeadStage).mockResolvedValue({ ...leads[1], stage: "meeting_scheduled" });
    vi.mocked(crmService.deleteLead).mockResolvedValue();
  });

  it("renders header, KPI strip, filter bar and stage summary", async () => {
    renderPage();

    expect(await screen.findByText("Ana Silva")).toBeInTheDocument();
    expect(screen.getByText("CRM")).toBeInTheDocument();
    expect(screen.getByText("Pipeline de conversao e gestao de leads")).toBeInTheDocument();
    expect(screen.getByText("Total ativos")).toBeInTheDocument();
    expect(screen.getByText("Em negociacao")).toBeInTheDocument();
    expect(screen.getByText("Fechados no mes")).toBeInTheDocument();
    expect(screen.getByText("Taxa de conversao")).toBeInTheDocument();
    expect(screen.getByText("Resumo por estagio")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Estagio" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Contato" })).toBeInTheDocument();
  });

  it("filters by stage/contact and clears all filters", async () => {
    renderPage();

    await screen.findByText("Ana Silva");

    fireEvent.change(screen.getByRole("combobox", { name: "Estagio" }), {
      target: { value: "proposal" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Contato" }), {
      target: { value: "stale_7" },
    });

    await waitFor(() => {
      expect(screen.getByText("Bruno Lima")).toBeInTheDocument();
      expect(screen.queryByText("Ana Silva")).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Limpar filtros/i }));

    await waitFor(() => {
      expect(screen.getByText("Ana Silva")).toBeInTheDocument();
      expect(screen.getByText("Bruno Lima")).toBeInTheDocument();
    });
  });

  it("advances the stage inline", async () => {
    renderPage();

    const leadRow = (await screen.findByText("Ana Silva")).closest('[role="button"]');
    expect(leadRow).not.toBeNull();

    fireEvent.click(within(leadRow as HTMLElement).getByRole("button", { name: /Avancar estagio/i }));

    await waitFor(() => {
      expect(crmService.updateLeadStage).toHaveBeenCalledWith("lead-1", "contact");
    });
  });

  it("opens the drawer, keeps the form sections and updates the lead without overwriting notes", async () => {
    renderPage();

    fireEvent.click(await screen.findByText("Bruno Lima"));

    expect(screen.getByText("Dados do lead")).toBeInTheDocument();
    expect(screen.getByText("Pipeline")).toBeInTheDocument();
    expect(screen.getByText("Historico comercial")).toBeInTheDocument();
    expect(screen.getByText("Precisa aprovar com a esposa.")).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue("Bruno Lima"), {
      target: { value: "Bruno Lima Prime" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alteracoes" }));

    await waitFor(() => {
      expect(crmService.updateLead).toHaveBeenCalledWith(
        "lead-2",
        expect.objectContaining({
          full_name: "Bruno Lima Prime",
          stage: "proposal",
        }),
      );
    });

    const [, payload] = vi.mocked(crmService.updateLead).mock.calls[0]!;
    expect(payload).not.toHaveProperty("notes");
  });

  it("appends notes to the commercial history without replacing previous entries", async () => {
    renderPage();

    fireEvent.click(await screen.findByText("Bruno Lima"));

    fireEvent.change(screen.getByPlaceholderText("Ex: cliente pediu retorno na sexta, prefere horario noturno."), {
      target: { value: "Cliente pediu retorno na sexta." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar ao historico" }));

    await waitFor(() => {
      expect(crmService.appendLeadNote).toHaveBeenCalledWith(
        "lead-2",
        expect.objectContaining({
          text: "Cliente pediu retorno na sexta.",
          entry_type: "note",
        }),
      );
    });
  });

  it("creates a new lead and preserves the delete flow for existing leads", async () => {
    renderPage();

    await screen.findByText("Ana Silva");

    fireEvent.click(screen.getAllByRole("button", { name: "Novo Lead" })[0]);
    fireEvent.change(screen.getByPlaceholderText("Nome completo"), {
      target: { value: "Diego Costa" },
    });
    fireEvent.change(screen.getByPlaceholderText("email@exemplo.com"), {
      target: { value: "diego@teste.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar Lead" }));

    await waitFor(() => {
      expect(crmService.createLead).toHaveBeenCalled();
    });
    expect(vi.mocked(crmService.createLead).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        full_name: "Diego Costa",
        email: "diego@teste.com",
      }),
    );

    fireEvent.click(screen.getByText("Ana Silva"));
    fireEvent.click(screen.getByRole("button", { name: "Remover Lead" }));
    fireEvent.click(screen.getByRole("button", { name: "Excluir" }));

    await waitFor(() => {
      expect(crmService.deleteLead).toHaveBeenCalledWith("lead-1");
    });
  });

  it("shows the empty state when there are no leads", async () => {
    vi.mocked(crmService.listLeads).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 200,
    });

    renderPage();

    expect(await screen.findByText("Nenhum lead encontrado")).toBeInTheDocument();
    expect(screen.getByText("Tente ajustar os filtros ou adicione um novo lead")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Novo Lead" }).length).toBeGreaterThan(0);
  });

  it("renders CRM in read-only mode for receptionist without mutation CTAs", async () => {
    authState.user = { id: "reception-1", full_name: "Recepcao Teste", role: "receptionist" };

    renderPage();

    fireEvent.click(await screen.findByText("Bruno Lima"));

    expect(screen.getByText("Detalhes do Lead")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salvar alteracoes" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Adicionar ao historico/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Avancar estagio/i })).not.toBeInTheDocument();
    expect(screen.queryAllByRole("button", { name: "Novo Lead" })).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Fechar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remover Lead" })).not.toBeInTheDocument();
  });
});
