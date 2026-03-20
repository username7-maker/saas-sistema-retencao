import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AssessmentsPage } from "../pages/assessments/AssessmentsPage";
import { assessmentService, type AssessmentDashboard } from "../services/assessmentService";

function memberWithDue<T extends string | null>(
  id: string,
  full_name: string,
  plan_name: string,
  risk_level: "green" | "yellow" | "red",
  risk_score: number,
  next_assessment_due: T,
  email = `${id}@teste.com`,
  last_checkin_at: string | null = null,
) {
  return {
    id,
    full_name,
    email,
    plan_name,
    risk_level,
    risk_score,
    last_checkin_at,
    extra_data: {},
    next_assessment_due,
  } as unknown as AssessmentDashboard["total_members_items"][number];
}

vi.mock("../services/assessmentService", async () => {
  const actual = await vi.importActual<typeof import("../services/assessmentService")>("../services/assessmentService");
  return {
    ...actual,
    assessmentService: {
      ...actual.assessmentService,
      dashboard: vi.fn(),
    },
  };
});

const dashboard: AssessmentDashboard = {
  total_members: 5,
  assessed_last_90_days: 3,
  overdue_assessments: 2,
  never_assessed: 1,
  upcoming_7_days: 1,
  total_members_items: [
    memberWithDue("member-1", "Ana Silva", "Plano Mensal", "red", 81, "2026-03-10T00:00:00Z", "ana@teste.com", "2026-03-10T10:00:00Z"),
    memberWithDue("member-2", "Bruno Lima", "Plano Anual", "yellow", 51, "2026-03-19T00:00:00Z", "bruno@teste.com", "2026-03-17T10:00:00Z"),
    memberWithDue("member-3", "Carla Nunes", "Plano Mensal", "yellow", 42, null, "carla@teste.com"),
  ],
  assessed_members: [
    memberWithDue("member-1", "Ana Silva", "Plano Mensal", "red", 81, "2026-03-10T00:00:00Z", "ana@teste.com", "2026-03-10T10:00:00Z"),
    memberWithDue("member-2", "Bruno Lima", "Plano Anual", "yellow", 51, "2026-03-19T00:00:00Z", "bruno@teste.com", "2026-03-17T10:00:00Z"),
  ],
  overdue_members: [
    memberWithDue("member-1", "Ana Silva", "Plano Mensal", "red", 81, "2026-03-10T00:00:00Z", "ana@teste.com", "2026-03-10T10:00:00Z"),
  ],
  never_assessed_members: [
    memberWithDue("member-3", "Carla Nunes", "Plano Mensal", "yellow", 42, null, "carla@teste.com"),
  ],
  upcoming_members: [
    memberWithDue("member-2", "Bruno Lima", "Plano Anual", "yellow", 51, "2026-03-19T00:00:00Z", "bruno@teste.com", "2026-03-17T10:00:00Z"),
  ],
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
  });

  it("renders the operational assessments queue by default", async () => {
    renderPage();

    expect(await screen.findByText("Central operacional")).toBeInTheDocument();
    expect(screen.getByText("Precisa de atencao agora")).toBeInTheDocument();
    expect(screen.getAllByText("Atrasadas").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Nunca avaliados").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Esta semana").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Abrir workspace").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Registrar avaliacao").length).toBeGreaterThan(0);
  });

  it("filters the queue for never assessed members", async () => {
    renderPage();

    await screen.findByText("Central operacional");
    fireEvent.click(screen.getByRole("button", { name: "Nunca avaliados" }));

    expect(screen.getAllByText("Carla Nunes").length).toBeGreaterThan(0);
    expect(screen.queryByText("Ana Silva")).not.toBeInTheDocument();
  });
});
