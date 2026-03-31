import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AssessmentsPage } from "../pages/assessments/AssessmentsPage";
import {
  assessmentService,
  type AssessmentDashboard,
  type AssessmentQueueItem,
  type AssessmentQueueResponse,
} from "../services/assessmentService";

function createQueueItem(
  id: string,
  fullName: string,
  bucket: AssessmentQueueItem["queue_bucket"],
  risk: AssessmentQueueItem["risk_level"],
  dueLabel: string,
  preferredShift: string | null = null,
): AssessmentQueueItem {
  return {
    id,
    full_name: fullName,
    email: `${id}@teste.com`,
    plan_name: "Plano Mensal",
    preferred_shift: preferredShift,
    risk_level: risk,
    risk_score: risk === "red" ? 82 : 45,
    last_checkin_at: "2026-03-18T10:00:00Z",
    next_assessment_due: bucket === "never" ? null : "2026-03-24",
    queue_bucket: bucket,
    coverage_label: bucket === "never" ? "Nenhuma avaliacao registrada" : "Cobertura vencida",
    due_label: dueLabel,
    urgency_score: bucket === "never" ? 380 : 310,
  };
}

vi.mock("../services/assessmentService", async () => {
  const actual = await vi.importActual<typeof import("../services/assessmentService")>("../services/assessmentService");
  return {
    ...actual,
    assessmentService: {
      ...actual.assessmentService,
      dashboard: vi.fn(),
      queue: vi.fn(),
      actuarSyncQueue: vi.fn().mockResolvedValue([]),
      updateQueueResolution: vi.fn().mockResolvedValue({
        member_id: "member-1",
        status: "scheduled",
        label: "Ja foi marcada",
        note: null,
        updated_at: "2026-03-27T12:00:00Z",
      }),
    },
  };
});

const dashboard: AssessmentDashboard = {
  total_members: 7300,
  assessed_last_90_days: 2200,
  overdue_assessments: 180,
  never_assessed: 320,
  upcoming_7_days: 41,
  historical_backlog_total: 910,
  historical_never_assessed: 640,
  historical_overdue_assessments: 270,
  attention_now: [createQueueItem("member-3", "Carla Nunes", "never", "yellow", "Primeira avaliacao pendente", "morning")],
  total_members_items: [],
  assessed_members: [],
  overdue_members: [],
  never_assessed_members: [],
  upcoming_members: [],
};

const queueAllPage1: AssessmentQueueResponse = {
  items: [
    createQueueItem("member-1", "Ana Silva", "overdue", "red", "Atrasada desde 10/03/2026", "morning"),
    createQueueItem("member-2", "Bruno Lima", "week", "yellow", "Janela ate 24/03/2026", "evening"),
  ],
  total: 3,
  page: 1,
  page_size: 2,
};

const queueAllPage2: AssessmentQueueResponse = {
  items: [createQueueItem("member-4", "Diego Alves", "covered", "green", "Sem proxima janela definida")],
  total: 3,
  page: 2,
  page_size: 2,
};

const queueNever: AssessmentQueueResponse = {
  items: [createQueueItem("member-3", "Carla Nunes", "never", "yellow", "Primeira avaliacao pendente", "morning")],
  total: 1,
  page: 1,
  page_size: 50,
};

const queueSearch: AssessmentQueueResponse = {
  items: [createQueueItem("member-5", "Erick Andrade", "upcoming", "yellow", "Proxima janela em 28/03/2026", "afternoon")],
  total: 1,
  page: 1,
  page_size: 50,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AssessmentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AssessmentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assessmentService.dashboard).mockResolvedValue(dashboard);
    vi.mocked(assessmentService.queue).mockImplementation(async (params) => {
      if (params?.search === "Erick") {
        return queueSearch;
      }
      if (params?.bucket === "never") {
        return queueNever;
      }
      if (params?.page === 2) {
        return queueAllPage2;
      }
      return queueAllPage1;
    });
  });

  it("renders dashboard summary and paginated queue", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Avaliacoes" })).toBeInTheDocument();
    expect(screen.getByText("Base ativa")).toBeInTheDocument();
    expect(screen.getByText("Precisa de atencao agora")).toBeInTheDocument();
    expect(screen.getByText(/ficaram fora da fila do dia por serem backlog historico/i)).toBeInTheDocument();
    expect(screen.getByText("Fila operacional")).toBeInTheDocument();
    expect(screen.getByText("Ana Silva")).toBeInTheDocument();
    expect(screen.getAllByText("Turno Manha").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Abrir workspace").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Registrar avaliacao").length).toBeGreaterThan(0);
    expect(screen.getByText("Pagina 1 de 2")).toBeInTheDocument();
  });

  it("changes bucket and resets the queue to matching results", async () => {
    renderPage();

    await screen.findByText("Ana Silva");
    fireEvent.click(screen.getByRole("button", { name: "Nunca avaliados" }));

    expect((await screen.findAllByText("Carla Nunes")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Ana Silva")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(assessmentService.queue).toHaveBeenLastCalledWith(
        expect.objectContaining({ bucket: "never", page: 1 }),
      );
    });
  });

  it("uses server-side search and paginates through the queue", async () => {
    renderPage();

    await screen.findByText("Ana Silva");
    fireEvent.click(screen.getByRole("button", { name: /^Proxima$/i }));
    expect(await screen.findByText("Diego Alves")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Buscar qualquer aluno ativo por nome, e-mail ou plano..."), {
      target: { value: "Erick" },
    });

    expect((await screen.findAllByText("Erick Andrade")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(assessmentService.queue).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "Erick", page: 1 }),
      );
    });
  });

  it("sends preferred shift filter to the queue endpoint", async () => {
    renderPage();

    await screen.findByText("Ana Silva");
    fireEvent.change(screen.getByRole("combobox", { name: "Turno" }), {
      target: { value: "morning" },
    });

    await waitFor(() => {
      expect(assessmentService.queue).toHaveBeenLastCalledWith(
        expect.objectContaining({ preferred_shift: "morning", page: 1 }),
      );
    });
  });

  it("allows resolving a pending assessment directly from the queue", async () => {
    renderPage();

    await screen.findByText("Ana Silva");
    const anaRow = screen.getByText("Ana Silva").closest("li");
    expect(anaRow).not.toBeNull();
    fireEvent.click(within(anaRow as HTMLElement).getByRole("button", { name: "Ja foi marcada" }));

    await waitFor(() => {
      expect(assessmentService.updateQueueResolution).toHaveBeenCalledWith("member-1", { status: "scheduled" });
    });
  });
});
