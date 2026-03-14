import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MemberProfile360Page } from "../pages/assessments/MemberProfile360Page";
import {
  assessmentService,
  normalizeAssessmentSummary360,
  type EvolutionData,
  type Profile360,
} from "../services/assessmentService";
import { memberTimelineService } from "../services/memberTimelineService";
import { memberService } from "../services/memberService";
import type { Member } from "../types";

vi.mock("../components/assessments/AssessmentTimeline", () => ({
  AssessmentTimeline: () => <div>Assessment timeline mock</div>,
}));

vi.mock("../components/assessments/EvolutionCharts", () => ({
  EvolutionCharts: () => <div>Evolution charts mock</div>,
}));

vi.mock("../components/assessments/GoalsProgress", () => ({
  GoalsProgress: () => <div>Goals progress mock</div>,
}));

vi.mock("../components/assessments/MemberBodyCompositionTab", () => ({
  MemberBodyCompositionTab: () => <div>Body composition mock</div>,
}));

vi.mock("../components/assessments/MemberConstraintsEditor", () => ({
  MemberConstraintsEditor: () => <div>Constraints editor mock</div>,
}));

vi.mock("../components/assessments/MemberGoalsEditor", () => ({
  MemberGoalsEditor: () => <div>Goals editor mock</div>,
}));

vi.mock("../components/assessments/MemberTrainingPlanEditor", () => ({
  MemberTrainingPlanEditor: () => <div>Training plan editor mock</div>,
}));

vi.mock("../components/common/MemberTimeline360Content", () => ({
  MemberTimeline360Content: () => <div>Timeline 360 mock</div>,
}));

vi.mock("../services/assessmentService", async () => {
  const actual = await vi.importActual<typeof import("../services/assessmentService")>("../services/assessmentService");
  return {
    ...actual,
    assessmentService: {
      ...actual.assessmentService,
      profile360: vi.fn(),
      list: vi.fn(),
      evolution: vi.fn(),
      summary360: vi.fn(),
    },
  };
});

vi.mock("../services/memberTimelineService", () => ({
  memberTimelineService: {
    list: vi.fn(),
  },
}));

vi.mock("../services/memberService", () => ({
  memberService: {
    getMember: vi.fn(),
    updateMember: vi.fn(),
  },
}));

const sparseProfile: Profile360 = {
  member: {
    id: "member-1",
    full_name: "Ana Silva",
    email: "ana@teste.com",
    plan_name: "Plano Mensal",
    risk_level: "yellow",
    risk_score: 54,
    last_checkin_at: null,
    extra_data: {},
  },
  latest_assessment: null,
  constraints: null,
  goals: [],
  active_training_plan: null,
  insight_summary: null,
};

const sparseEvolution: EvolutionData = {
  labels: [],
  weight: [],
  body_fat: [],
  lean_mass: [],
  bmi: [],
  strength: [],
  flexibility: [],
  cardio: [],
  checkins_labels: [],
  checkins_per_month: [],
  main_lift_load: [],
  main_lift_label: null,
  deltas: {},
};

const minimalMember: Member = {
  id: "member-1",
  full_name: "Ana Silva",
  email: "ana@teste.com",
  phone: null,
  status: "active",
  plan_name: "Plano Mensal",
  monthly_fee: 199,
  join_date: "2026-03-01",
  preferred_shift: null,
  nps_last_score: 8,
  loyalty_months: 1,
  risk_score: 54,
  risk_level: "yellow",
  last_checkin_at: null,
  extra_data: {},
  suggested_action: null,
  onboarding_status: null,
  onboarding_score: null,
  created_at: "2026-03-01T00:00:00Z",
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
      <MemoryRouter initialEntries={["/assessments/members/member-1"]}>
        <Routes>
          <Route path="/assessments/members/:memberId" element={<MemberProfile360Page />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MemberProfile360Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(assessmentService.profile360).mockResolvedValue(sparseProfile);
    vi.mocked(assessmentService.list).mockResolvedValue([]);
    vi.mocked(assessmentService.evolution).mockResolvedValue(sparseEvolution);
    vi.mocked(assessmentService.summary360).mockResolvedValue(
      normalizeAssessmentSummary360({
        member: sparseProfile.member,
        goal_type: "fat_loss",
      }),
    );
    vi.mocked(memberTimelineService.list).mockResolvedValue([]);
    vi.mocked(memberService.getMember).mockResolvedValue(minimalMember);
    vi.mocked(memberService.updateMember).mockResolvedValue(minimalMember);
  });

  it("renders safely with sparse intelligence payload", async () => {
    renderPage();

    expect(await screen.findAllByText("Sem avaliacao estruturada")).toHaveLength(2);
    expect(screen.getByText("Sem benchmark")).toBeInTheDocument();
    expect(screen.getByText("dados insuficientes")).toBeInTheDocument();
    expect(screen.queryByText(/algo deu errado/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Diagnostico IA" }));
    expect(await screen.findByText("Sem sinais suficientes de evolucao registrados.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Acoes" }));
    expect(await screen.findByText("Sem acoes recomendadas enquanto nao houver dados suficientes.")).toBeInTheDocument();
  });
});
