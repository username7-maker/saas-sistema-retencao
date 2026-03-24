import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OperationalDashboardPage } from "../pages/dashboard/OperationalDashboardPage";

vi.mock("../hooks/useDashboard", () => ({
  useOperationalDashboard: () => ({
    isLoading: false,
    isError: false,
    data: {
      realtime_checkins: 12,
      heatmap: [],
      inactive_7d_total: 3,
      inactive_7d_items: [],
      birthday_today_total: 2,
      birthday_today_items: [
        {
          id: "member-1",
          full_name: "Ana Silva",
          email: "ana@teste.com",
          phone: "11999990001",
          birthdate: "1990-03-24",
          status: "active",
          plan_name: "Plano Mensal",
          monthly_fee: 199,
          join_date: "2026-01-10",
          preferred_shift: null,
          nps_last_score: 8,
          loyalty_months: 3,
          risk_score: 32,
          risk_level: "green",
          last_checkin_at: "2026-03-24T08:00:00Z",
          extra_data: {},
          suggested_action: null,
          onboarding_status: "active",
          onboarding_score: 0,
          created_at: "2026-01-10T00:00:00Z",
          updated_at: "2026-03-24T00:00:00Z",
        },
      ],
    },
    refetch: vi.fn(),
    error: null,
  }),
}));

vi.mock("../services/storage", () => ({
  tokenStorage: {
    getAccessToken: () => null,
  },
}));

vi.mock("../components/charts/HeatmapGrid", () => ({
  HeatmapGrid: () => <div>Heatmap mock</div>,
}));

vi.mock("../components/common/AiInsightCard", () => ({
  AiInsightCard: () => <div>Insight mock</div>,
}));

vi.mock("../components/common/DashboardActions", () => ({
  DashboardActions: () => <div>Actions mock</div>,
}));

vi.mock("../components/common/QuickActions", () => ({
  QuickActions: () => <div>Quick actions mock</div>,
}));

describe("OperationalDashboardPage", () => {
  it("renders the birthdays section for today", () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <OperationalDashboardPage />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Aniversariantes de hoje")).toBeInTheDocument();
    expect(screen.getByText("2 hoje")).toBeInTheDocument();
    expect(screen.getByText("Ana Silva")).toBeInTheDocument();
  });
});
