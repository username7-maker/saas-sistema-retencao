import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MemberDetailDrawer } from "../pages/members/MemberDetailDrawer";
import { normalizeAssessmentSummary360 } from "../services/assessmentService";
import { lgpdService } from "../services/lgpdService";
import { memberService } from "../services/memberService";
import type { Member } from "../types";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "owner-1",
      gym_id: "gym-1",
      full_name: "Owner Teste",
      email: "owner@teste.com",
      role: "owner",
      is_active: true,
      created_at: "2026-03-01T00:00:00Z",
    },
  }),
}));

vi.mock("../components/common/QuickActions", () => ({
  QuickActions: () => <div>Acoes rapidas mock</div>,
}));

vi.mock("../services/lgpdService", () => ({
  lgpdService: {
    getMemberConsents: vi.fn(),
    recordMemberConsent: vi.fn(),
    exportMemberPdf: vi.fn(),
    anonymizeMember: vi.fn(),
  },
}));

vi.mock("../services/memberService", () => ({
  memberService: {
    getOnboardingScore: vi.fn(),
    getProfile360: vi.fn(),
    getAssessmentSummary: vi.fn(),
  },
}));

const member: Member = {
  id: "member-1",
  full_name: "Taciane Brezolin",
  email: "taciane@teste.com",
  phone: "11999990001",
  status: "active",
  plan_name: "Plano Mensal",
  monthly_fee: 199,
  join_date: "2026-03-01",
  preferred_shift: null,
  nps_last_score: 8,
  loyalty_months: 1,
  risk_score: 88,
  risk_level: "red",
  last_checkin_at: null,
  extra_data: {},
  suggested_action: null,
  onboarding_status: null,
  onboarding_score: null,
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-10T00:00:00Z",
};

function renderDrawer() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemberDetailDrawer member={member} open onClose={vi.fn()} />
    </QueryClientProvider>,
  );
}

describe("MemberDetailDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(lgpdService.getMemberConsents).mockResolvedValue({ current: [] } as never);
    vi.mocked(memberService.getProfile360).mockResolvedValue({} as never);
    vi.mocked(memberService.getAssessmentSummary).mockResolvedValue(
      normalizeAssessmentSummary360({
        member,
        status: "critical",
        forecast: {
          probability_60d: 31,
          corrected_probability_90d: 53,
          corrected_summary: "Cenario corrigido com chance moderada se houver acao.",
        },
        narratives: {
          retention_summary: "Risco alto por baixa consistencia de frequencia.",
        },
        next_best_action: {
          key: "activate_frequency",
          title: "Ativar frequencia de Taciane Brezolin",
          reason: "Baixa consistencia de treino nas primeiras semanas.",
          suggested_message: "Vamos reorganizar sua rotina?",
        },
        actions: [
          {
            key: "activate_frequency",
            title: "Ativar frequencia de Taciane Brezolin",
            reason: "Baixa consistencia de treino nas primeiras semanas.",
          },
        ],
      }),
    );
  });

  it("renders the retention tab with dark-safe operational blocks", async () => {
    renderDrawer();

    fireEvent.click(screen.getByRole("button", { name: "Retencao" }));

    const probability = await screen.findByText("31% em 60 dias");
    expect(probability).toHaveClass("text-lovable-danger");
    expect(screen.getByText("Forecast corrigido")).toBeInTheDocument();
    expect(screen.getByText("Narrativa de retencao")).toBeInTheDocument();
    expect(screen.getByText("Proxima acao recomendada")).toBeInTheDocument();
    expect(screen.getByText("Playbook sugerido")).toBeInTheDocument();
    expect(screen.getAllByText("Ativar frequencia de Taciane Brezolin").length).toBeGreaterThan(0);
  });
});
